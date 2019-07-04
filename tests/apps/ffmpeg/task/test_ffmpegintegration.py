import os
import logging

from ffmpeg_tools.codecs import VideoCodec
from ffmpeg_tools.formats import Container, list_matching_resolutions, \
    list_supported_frame_rates
from ffmpeg_tools.validation import UnsupportedVideoCodec, InvalidResolution, \
    UnsupportedVideoCodecConversion, InvalidFrameRate

from parameterized import parameterized
import pytest

from apps.transcoding.common import TranscodingTaskBuilderException, \
    ffmpegException
from apps.transcoding.ffmpeg.task import ffmpegTaskTypeInfo
from golem.testutils import TestTaskIntegration, \
    remove_temporary_dirtree_if_test_passed
from golem.tools.ci import ci_skip
from tests.apps.ffmpeg.task.utils.ffprobe_report_set import FfprobeReportSet
from tests.apps.ffmpeg.task.utils.simulated_transcoding_operation import \
    SimulatedTranscodingOperation

logger = logging.getLogger(__name__)


@ci_skip
class TestFfmpegIntegration(TestTaskIntegration):

    # pylint: disable=line-too-long,bad-whitespace
    VIDEO_FILES = [
        # Files from the repo (good)
        {"resolution": [320, 240],   "container": Container.c_MP4,      "video_codec": VideoCodec.H_264,     "path": "test_video.mp4"},
        {"resolution": [320, 240],   "container": Container.c_MP4,      "video_codec": VideoCodec.H_264,     "path": "test_video2"},

        # Files from transcoding-video-bundle (good)
        {"resolution": [512, 288],   "container": Container.c_WEBM,     "video_codec": VideoCodec.VP8,       "path": "videos/good/basen-out8[vp8,512x288,10s,v1a0s0d0,i248p494b247,25fps].webm"},
        {"resolution": [512, 288],   "container": Container.c_WEBM,     "video_codec": VideoCodec.VP9,       "path": "videos/good/basen-out9[vp9,512x288,10s,v1a0s0d0,i248p494b247,25fps].webm"},
        {"resolution": [1920, 1080], "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/good/beachfront-dandelion[mpeg2video+mp2,1920x1080,20s,v1a1s0d0,i1765p1925b1604,23.976fps][segment1of11].mpeg"},
        {"resolution": [1920, 1080], "container": Container.c_ASF,      "video_codec": VideoCodec.WMV3,      "path": "videos/good/beachfront-mooncloseup[wmv3,1920x1080,34s,v1a0s0d0,i799p1578b792,24fps][segment1of7].wmv"},
        {"resolution": [1920, 1080], "container": Container.c_ASF,      "video_codec": VideoCodec.WMV3,      "path": "videos/good/beachfront-sleepingbee[wmv3+wmapro,1920x1080,47s,v1a1s0d0,i1135p2241b1125,24fps][segment1of10].wmv"},
        {"resolution": [1920, 960],  "container": Container.c_MATROSKA, "video_codec": VideoCodec.HEVC,      "path": "videos/good/h265files-alps[hevc+aac,1920x960,16s,v1a1s0d0,i401p478b718,25fps][segment1of2].mkv"},
        {"resolution": [854, 480],   "container": Container.c_MATROSKA, "video_codec": VideoCodec.MSMPEG4V2, "path": "videos/good/matroska-test1[msmpeg4v2+mp3,854x480,87s,v1a1s0d0,i4215p6261b4190,24fps][segment1of10].mkv"},
        {"resolution": [1024, 576],  "container": Container.c_MATROSKA, "video_codec": VideoCodec.H_264,     "path": "videos/good/matroska-test5[h264+aac+aac,1024x576,47s,v1a2s8d0,i1149p1655b1609,24fps][segment1of10].mkv"},
        {"resolution": [1280, 720],  "container": Container.c_ASF,      "video_codec": VideoCodec.WMV3,      "path": "videos/good/natureclip-fireandembers[wmv3+wmav2,1280x720,63s,v1a1s0d0,i2240p3428b1889,29.97fps][segment1of13].wmv"},
        {"resolution": [176, 144],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/sample-bigbuckbunny[h263+amr_nb,176x144,41s,v1a1s0d0,i1269p1777b1218,15fps][segment1of9].3gp"},
        {"resolution": [1280, 720],  "container": Container.c_MATROSKA, "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/sample-bigbuckbunny[mpeg4+aac,1280x720,4s,v1a1s0d0,i293p438b292,25fps].mkv"},
        {"resolution": [320, 240],   "container": Container.c_3GP,      "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/sample-bigbuckbunny[mpeg4+aac,320x240,15s,v1a1s0d0,i780p1091b748,25fps][segment1of3].3gp"},
        {"resolution": [640, 368],   "container": Container.c_MP4,      "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/sample-bigbuckbunny[mpeg4+aac,640x368,6s,v1a1s0d0,i319p477b318,25fps].mp4"},
        {"resolution": [560, 320],   "container": Container.c_AVI,      "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/standalone-bigbuckbunny[mpeg4+mp3,560x320,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].avi"},
        {"resolution": [180, 140],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV3,      "path": "videos/good/standalone-catherine[wmv3+wmav2,180x140,42s,v1a1s0d0,i637p1257b631,_][segment1of6].wmv"},
        {"resolution": [400, 300],   "container": Container.c_MOV,      "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-dlppart2[h264+aac,400x300,129s,v1a1s0d0,i3874p4884b6671,29.97fps][segment1of17].mov"},
        {"resolution": [720, 480],   "container": Container.c_IPOD,     "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-dolbycanyon[h264+aac,720x480,38s,v1a1s0d0,i1147p1466b1948,29.97fps][segment1of5].m4v"},
        {"resolution": [720, 480],   "container": Container.c_FLV,      "video_codec": VideoCodec.FLV1,      "path": "videos/good/standalone-grb2[flv1,720x480,28s,v1a0s0d0,i1743p2428b1668,29.9697fps][segment1of6].flv"},
        {"resolution": [720, 480],   "container": Container.c_IPOD,     "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-grb2[h264,720x480,28s,v1a0s0d0,i840p1060b1437,29.97fps][segment1of4].m4v"},
        {"resolution": [720, 480],   "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/good/standalone-grb2[mpeg2video,720x480,28s,v1a0s0d0,i2596p2783b3103,29.97fps].mpg"},
        {"resolution": [720, 480],   "container": Container.c_SVCD,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/good/standalone-grb2[mpeg2video,720x480,28s,v1a0s0d0,i2656p3337b2579,29.97fps][segment1of6].vob"},
        {"resolution": [720, 480],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV2,      "path": "videos/good/standalone-grb2[wmv2,720x480,28s,v1a0s0d0,i1744p2427b1668,29.97fps][segment1of6].wmv"},
        {"resolution": [1920, 1080], "container": Container.c_FLV,      "video_codec": VideoCodec.FLV1,      "path": "videos/good/standalone-jellyfish[flv1,1920x1080,30s,v1a0s0d0,i1874p2622b1798,29.9697fps][segment1of8].flv"},
        {"resolution": [1408, 1152], "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/standalone-jellyfish[h263,1408x1152,30s,v1a0s0d0,i1874p2622b1798,29.97fps][segment1of8].3gp"},
        {"resolution": [1920, 1080], "container": Container.c_MATROSKA, "video_codec": VideoCodec.HEVC,      "path": "videos/good/standalone-jellyfish[hevc,1920x1080,30s,v1a0s0d0,i903p1123b1571,29.97fps][segment1of4].mkv"},
        {"resolution": [384, 288],   "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_1,    "path": "videos/good/standalone-lion[mpeg1video+mp2,384x288,117s,v1a1s0d0,i8738p9088b10660,23.976fps][segment1of24].mpeg"},
        {"resolution": [320, 240],   "container": Container.c_MP4,      "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-p6090053[h264+aac,320x240,30s,v1a1s0d0,i376p468b653,12.5fps][segment1of2].mp4"},
        {"resolution": [320, 240],   "container": Container.c_MOV,      "video_codec": VideoCodec.MJPEG,     "path": "videos/good/standalone-p6090053[mjpeg+pcm_u8,320x240,30s,v1a1s0d0,i1123p748b748,12.5fps][segment1of10].mov"},
        {"resolution": [480, 270],   "container": Container.c_FLV,      "video_codec": VideoCodec.FLV1,      "path": "videos/good/standalone-page18[flv1+mp3,480x270,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].flv"},
        {"resolution": [352, 288],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/standalone-page18[h263+amr_nb,352x288,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].3gp"},
        {"resolution": [480, 270],   "container": Container.c_IPOD,     "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-page18[h264+aac,480x270,216s,v1a1s0d0,i5446p10755b5400,25fps][segment1of43].m4v"},
        {"resolution": [480, 270],   "container": Container.c_AVI,      "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/standalone-page18[mpeg4+mp3,480x270,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].avi"},
        {"resolution": [1920, 1080], "container": Container.c_MPEGTS,   "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-panasonic[h264+ac3,1920x1080,46s,v1a1s1d0,i1247p1439b1919,25fps][segment1of10].mts"},
        {"resolution": [1920, 1080], "container": Container.c_AVI,      "video_codec": VideoCodec.MPEG_4,    "path": "videos/good/standalone-panasonic[mpeg4+mp3,1920x1080,46s,v1a1s0d0,i2401p3355b2302,25fps][segment1of10].avi"},
        {"resolution": [352, 288],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/standalone-small[h263+amr_nb,352x288,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].3gp"},
        {"resolution": [560, 320],   "container": Container.c_MPEGTS,   "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-small[h264+ac3,560x320,6s,v1a1s0d0,i166p211b284,29.97fps].mts"},
        {"resolution": [560, 320],   "container": Container.c_MATROSKA, "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-small[h264+vorbis,560x320,6s,v1a1s0d0,i166p211b284,30fps].mkv"},
        {"resolution": [560, 320],   "container": Container.c_SVCD,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/good/standalone-small[mpeg2video+mp2,560x320,6s,v1a1s0d0,i523p661b509,30fps][segment1of2].vob"},
        {"resolution": [560, 320],   "container": Container.c_WEBM,     "video_codec": VideoCodec.VP8,       "path": "videos/good/standalone-small[vp8+vorbis,560x320,6s,v1a1s0d0,i166p330b165,30fps].webm"},
        {"resolution": [560, 320],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV2,      "path": "videos/good/standalone-small[wmv2+wmav2,560x320,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].wmv"},
        {"resolution": [1280, 720],  "container": Container.c_FLV,      "video_codec": VideoCodec.FLV1,      "path": "videos/good/standalone-startrails[flv1+mp3,1280x720,21s,v1a1s0d0,i1101p1540b1056,25fps][segment1of5].flv"},
        {"resolution": [704, 576],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/standalone-startrails[h263+amr_nb,704x576,21s,v1a1s0d0,i1101p1540b1056,25fps][segment1of5].3gp"},
        {"resolution": [1280, 720],  "container": Container.c_WEBM,     "video_codec": VideoCodec.VP9,       "path": "videos/good/standalone-startrails[vp9+opus,1280x720,21s,v1a1s0d0,i533p1052b528,25fps][segment1of5].webm"},
        {"resolution": [704, 576],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/good/standalone-tra3106[h263,704x576,17s,v1a0s0d0,i1069p1472b1016,29.97fps][segment1of5].3gp"},
        {"resolution": [720, 496],   "container": Container.c_AVI,      "video_codec": VideoCodec.MJPEG,     "path": "videos/good/standalone-tra3106[mjpeg,720x496,17s,v1a0s0d0,i1525p1016b1016,29.97fps][segment1of17].avi"},
        {"resolution": [320, 240],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV1,      "path": "videos/good/standalone-video1[wmv1+wmav2,320x240,12s,v1a1s0d0,i703p1048b700,30fps][segment1of2].wmv"},
        {"resolution": [320, 240],   "container": Container.c_FLV,      "video_codec": VideoCodec.FLV1,      "path": "videos/good/standalone-videosample[flv1,320x240,59s,v1a0s0d0,i491p625b446,_][segment1of12].flv"},
        {"resolution": [320, 240],   "container": Container.c_MPEGTS,   "video_codec": VideoCodec.H_264,     "path": "videos/good/standalone-videosample[h264,320x240,59s,v1a0s0d0,i224p279b390,29.97fps].mts"},
        {"resolution": [320, 240],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV2,      "path": "videos/good/techslides-small[wmv2+wmav2,320x240,6s,v1a1s0d0,i331p495b330,30fps].wmv"},
        {"resolution": [640, 360],   "container": Container.c_WEBM,     "video_codec": VideoCodec.VP8,       "path": "videos/good/webmfiles-bigbuckbunny[vp8+vorbis,640x360,32s,v1a1s0d0,i837p1597b811,25fps][segment1of7].webm"},
        {"resolution": [640, 480],   "container": Container.c_ASF,      "video_codec": VideoCodec.WMV3,      "path": "videos/good/wfu-katamari[wmv3+wmav2,640x480,10s,v1a1s0d0,i301p597b299,29.97fps][segment1of2].wmv"},
        {"resolution": [3840, 2160], "container": Container.c_WEBM,     "video_codec": VideoCodec.VP8,       "path": "videos/good/wikipedia-globaltemp[vp8+vorbis,3840x2160,37s,v1a1s0d0,i1194p2113b1102,30fps][segment1of8].webm"},
        {"resolution": [1920, 1080], "container": Container.c_WEBM,     "video_codec": VideoCodec.VP8,       "path": "videos/good/wikipedia-tractor[vp8+vorbis,1920x1080,28s,v1a1s0d0,i695p1373b689,1000fps][segment1of5].webm"},
        {"resolution": [854, 480],   "container": Container.c_WEBM,     "video_codec": VideoCodec.VP9,       "path": "videos/good/wikipedia-tractor[vp9+opus,854x480,28s,v1a1s0d0,i692p1376b689,25fps][segment1of3].webm"},
        {"resolution": [854, 480],   "container": Container.c_WEBM,     "video_codec": VideoCodec.AV1,       "path": "videos/good/woolyss-llamadrama[av1+opus,854x480,87s,v1a1s0d0,i1879p1879b1879,24fps].webm"},

        # Files from the repo (bad)
        {"resolution": [320, 240],   "container": Container.c_MP4,      "video_codec": VideoCodec.H_264,     "path": "invalid_test_video.mp4"},

        # Files from transcoding-video-bundle (bad)
        {"resolution": [1920, 1080], "container": Container.c_MOV,      "video_codec": VideoCodec.MJPEG,     "path": "videos/bad/beachfront-moonandclouds[mjpeg,1920x1080,50s,v1a0s0d1,i3574p2382b2382,24fps].mov"},
        {"resolution": [1920, 1080], "container": Container.c_MOV,      "video_codec": VideoCodec.MJPEG,     "path": "videos/bad/beachfront-mooncloseup[mjpeg,1920x1080,33s,v1a0s0d1,i2374p1582b1582,23.976fps].mov"},
        {"resolution": [1280, 720],  "container": Container.c_MATROSKA, "video_codec": VideoCodec.THEORA,    "path": "videos/bad/matroska-test4[theora+vorbis,1280x720,_,v1a1s0d0,i1677p3247b1641,24fps].mkv"},
        {"resolution": [1920, 1080], "container": Container.c_MOV,      "video_codec": VideoCodec.H_264,     "path": "videos/bad/natureclip-relaxriver[h264+aac,1920x1080,20s,v1a1s0d1,i606p1192b599,29.97fps].mov"},
        {"resolution": [704, 576],   "container": Container.c_3GP,      "video_codec": VideoCodec.H_263,     "path": "videos/bad/standalone-dolbycanyon[h263+amr_nb,704x576,38s,v1a1s0d0,i2376p3325b2280,29.97fps].3gp"},
        {"resolution": [720, 480],   "container": Container.c_SVCD,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/bad/standalone-dolbycanyon[mpeg2video+ac3,720x480,38s,v1a1s0d1,i3574p3801b4257,29.97fps].vob"},
        {"resolution": [560, 320],   "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/bad/standalone-small[mpeg2video+mp2,560x320,6s,v1a1s0d1,i523p661b509,30fps].mpg"},
        {"resolution": [720, 496],   "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/bad/standalone-tra3106[mpeg2video,720x496,17s,v1a0s0d1,i1642p2033b1583,29.97fps].mpeg"},
        {"resolution": [320, 240],   "container": Container.c_MPEG,     "video_codec": VideoCodec.MPEG_2,    "path": "videos/bad/standalone-videosample[mpeg2video,320x240,59s,v1a0s0d1,i45135p57013b43947,240fps].mpg"},
        {"resolution": [560, 320],   "container": Container.c_OGG,      "video_codec": VideoCodec.THEORA,    "path": "videos/bad/techslides-small[theora+vorbis,560x320,6s,v1a1s0d1,i168p328b165,30fps].ogv"},
    ]
    # pylint: enable=line-too-long,bad-whitespace

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._ffprobe_report_set = FfprobeReportSet()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        report_file_name = os.path.join(
            cls.root_dir,
            'ffmpeg-integration-test-transcoding-diffs.md'
        )
        with open(report_file_name, 'w') as file:
            file.write(cls._ffprobe_report_set.to_markdown())

    def setUp(self):
        super().setUp()

        # We'll be comparing output from FfprobeFormatReport.diff() which
        # can be long but we still want to see it all.
        self.maxDiff = None

        self.RESOURCES = os.path.join(os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))), 'resources')
        self.tt = ffmpegTaskTypeInfo()

    @classmethod
    def _create_task_def_for_transcoding(  # pylint: disable=too-many-arguments
            cls,
            resource_stream,
            result_file,
            container,
            video_options=None,
            subtasks_count=2,
    ):
        task_def_for_transcoding = {
            'type': 'FFMPEG',
            'name': os.path.splitext(os.path.basename(result_file))[0],
            'timeout': '0:10:00',
            'subtask_timeout': '0:09:50',
            'subtasks_count': subtasks_count,
            'bid': 1.0,
            'resources': [resource_stream],
            'options': {
                'output_path': os.path.dirname(result_file),
                'video': video_options if video_options is not None else {},
                'container': container,
            }
        }

        return task_def_for_transcoding

    @parameterized.expand(
        (video, video_codec, container)
        for video in VIDEO_FILES
        for video_codec, container in [
            (VideoCodec.FLV1, Container.c_FLV),
            (VideoCodec.H_264, Container.c_AVI),
            (VideoCodec.H_265, Container.c_MP4),
            (VideoCodec.HEVC, Container.c_MP4),
            (VideoCodec.MJPEG, Container.c_MOV),
            (VideoCodec.MPEG_1, Container.c_MPEG),
            (VideoCodec.MPEG_2, Container.c_MPEG),
            (VideoCodec.MPEG_4, Container.c_MPEGTS),
            (VideoCodec.THEORA, Container.c_OGG),
            (VideoCodec.VP8, Container.c_WEBM),
            (VideoCodec.VP9, Container.c_MATROSKA),
            (VideoCodec.WMV1, Container.c_ASF),
            (VideoCodec.WMV2, Container.c_ASF),
        ]
    )
    @pytest.mark.slow
    @remove_temporary_dirtree_if_test_passed
    def test_split_and_merge_with_codec_change(self,
                                               video,
                                               video_codec,
                                               container):
        assert Container.is_supported(container.value)
        assert container.is_supported_video_codec(video_codec.value)

        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="codec change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir,
            dont_include_in_option_description=["resolution"])
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_video_codec_change(video_codec)
        if video_codec == VideoCodec.H_265:
            operation.set_override('video', 'codec_name', VideoCodec.HEVC.value)
        operation.request_container_change(container)
        operation.request_resolution_change(video["resolution"])
        operation.exclude_from_diff({'video': {'bitrate', 'frame_count'}})

        supported_conversions = video["video_codec"].get_supported_conversions()
        if video_codec.value in supported_conversions:
            (_input_report, _output_report, diff) = operation.run(video["path"])
            self.assertEqual(diff, [])
        else:
            with self.assertRaises(UnsupportedVideoCodecConversion):
                operation.run(video["path"])

    @parameterized.expand(
        (video, resolution)
        for video in VIDEO_FILES
        for resolution in (
            [320, 240],
            [640, 260],
            [640, 480],
        )
    )
    @pytest.mark.slow
    @remove_temporary_dirtree_if_test_passed
    def test_split_and_merge_with_resolution_change(self, video, resolution):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="resolution change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_resolution_change(resolution)
        operation.request_video_codec_change(video['video_codec'])
        operation.request_container_change(video['container'])
        operation.exclude_from_diff({'video': {'bitrate'}})

        supported_conversions = video["video_codec"].get_supported_conversions()
        if video["video_codec"].value not in supported_conversions:
            pytest.skip("Transcoding is not possible for this file without"
                        "also changing the video codec.")

        if resolution in list_matching_resolutions(video["resolution"]):
            (_input_report, _output_report, diff) = operation.run(video["path"])
            self.assertEqual(diff, [])
        else:
            with self.assertRaises(InvalidResolution):
                operation.run(video["path"])

    @parameterized.expand(
        (video, frame_rate)
        for video in VIDEO_FILES
        for frame_rate in (1, 25, '30000/1001', 60)
    )
    @pytest.mark.slow
    @remove_temporary_dirtree_if_test_passed
    def test_split_and_merge_with_frame_rate_change(self, video, frame_rate):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="frame rate change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir,
            dont_include_in_option_description=["resolution", "video_codec"])
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_frame_rate_change(frame_rate)
        operation.request_video_codec_change(video['video_codec'])
        operation.request_container_change(video['container'])
        operation.request_resolution_change(video["resolution"])
        operation.exclude_from_diff({'video': {'bitrate', 'frame_count'}})

        supported_conversions = video["video_codec"].get_supported_conversions()
        if video["video_codec"].value not in supported_conversions:
            pytest.skip("Transcoding is not possible for this file without"
                        "also changing the video codec.")

        if set([frame_rate, str(frame_rate)]) & list_supported_frame_rates() != set():
            (_input_report, _output_report, diff) = operation.run(video["path"])
            self.assertEqual(diff, [])
        else:
            with self.assertRaises(InvalidFrameRate):
                operation.run(video["path"])

    @parameterized.expand(
        (video, subtasks_count)
        for video in VIDEO_FILES
        for subtasks_count in (1, 6, 10)
    )
    @pytest.mark.slow
    @remove_temporary_dirtree_if_test_passed
    def test_split_and_merge_with_different_subtask_counts(self,
                                                           video,
                                                           subtasks_count):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="number of subtasks",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir,
            dont_include_in_option_description=["resolution", "video_codec"])
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_subtasks_count(subtasks_count)
        operation.request_video_codec_change(video['video_codec'])
        operation.request_container_change(video['container'])
        operation.request_resolution_change(video["resolution"])
        operation.exclude_from_diff({'video': {'bitrate'}})

        supported_conversions = video["video_codec"].get_supported_conversions()
        if video["video_codec"].value not in supported_conversions:
            pytest.skip("Transcoding is not possible for this file without"
                        "also changing the video codec.")

        (_input_report, _output_report, diff) = operation.run(video["path"])
        self.assertEqual(diff, [])

    @remove_temporary_dirtree_if_test_passed
    def test_simple_case(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2')
        result_file = os.path.join(self.root_dir, 'test_simple_case.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            container=Container.c_MP4.value,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        task = self.execute_task(task_def)
        result = task.task_definition.output_file
        self.assertTrue(TestTaskIntegration.check_file_existence(result))

    @remove_temporary_dirtree_if_test_passed
    def test_nonexistent_output_dir(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2')
        result_file = os.path.join(self.root_dir, 'nonexistent', 'path',
                                   'test_invalid_task_definition.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            container=Container.c_MP4.value,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        task = self.execute_task(task_def)

        result = task.task_definition.output_file
        self.assertTrue(TestTaskIntegration.check_file_existence(result))
        self.assertTrue(TestTaskIntegration.check_dir_existence(
            os.path.dirname(result_file)))

    @remove_temporary_dirtree_if_test_passed
    def test_nonexistent_resource(self):
        resource_stream = os.path.join(self.RESOURCES,
                                       'test_nonexistent_video.mp4')

        result_file = os.path.join(self.root_dir, 'test_nonexistent_video.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            container=Container.c_MP4.value,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(TranscodingTaskBuilderException):
            self.execute_task(task_def)

    @remove_temporary_dirtree_if_test_passed
    def test_invalid_resource_stream(self):
        resource_stream = os.path.join(self.RESOURCES, 'invalid_test_video.mp4')
        result_file = os.path.join(self.root_dir,
                                   'test_invalid_resource_stream.mp4')

        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            container=Container.c_MP4.value,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(ffmpegException):
            self.execute_task(task_def)

    @remove_temporary_dirtree_if_test_passed
    def test_task_invalid_params(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2')
        result_file = os.path.join(self.root_dir, 'test_invalid_params.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            container=Container.c_MP4.value,
            video_options={
                'codec': 'abcd',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(UnsupportedVideoCodec):
            self.execute_task(task_def)
