import json
import os
from typing import List, Optional

from ..render_tools import blender_render as blender

from .crop_generator import WORK_DIR, OUTPUT_DIR, SubImage, Region, \
    generate_single_random_crop_data, Crop
from .img_metrics_calculator import calculate_metrics, get_raw_verification



# todo review: too many blank lines
def get_crop_with_id(id: int, crops: [List[Crop]]) -> Optional[Crop]:
    for crop in crops:
        if crop.id == id:
            return crop
    return None


# todo review: this function is too long
# todo review: name should indicate that a list of Crop instances is also
#  returned  - find better name
# todo review: clarify what are "params" - find better name
def prepare_params(  # pylint: disable=too-many-locals, too-many-arguments
        subtask_border,
        scene_file_path,
        resolution,
        samples,
        frames,
        output_format,
        crops_count=3,
        crops_borders=None
):
    subimage = SubImage(
        Region(
            subtask_border[0],
            subtask_border[1],
            subtask_border[2],
            subtask_border[3]
        ),
        resolution
    )
    crops: List[Crop] = []
    crops_render_data = []

    # todo review: clean the TODO
    if crops_borders:  # TODO: Allow verification with given crops_border!
        # todo review: rename to "crop_id"
        idx = 0
        for border in crops_borders:
            crop = Crop.create_from_region(
                idx,
                Region(border[0], border[1], border[2], border[3]),
                subimage
            )
            crops_render_data.append(
                {
                    "id": crop.id,
                    "outfilebasename": "crop" + str(idx) + '_',
                    "borders_x": [crop.crop_region.left,
                                  crop.crop_region.right],
                    "borders_y": [crop.crop_region.top, crop.crop_region.bottom]
                }
            )
            crops.append(crop)
            idx += 1
    else:
        for i in range(0, crops_count):
            crop = generate_single_random_crop_data(
                subimage,
                i
            )
            crops_render_data.append(
                {
                    "id": crop.id,
                    "outfilebasename": "crop" + str(i) + '_',
                    "borders_x": [crop.crop_region.left,
                                  crop.crop_region.right],
                    "borders_y": [crop.crop_region.top, crop.crop_region.bottom]
                }
            )
            crops.append(crop)

    params = {
        "scene_file": scene_file_path,
        "resolution": resolution,
        "use_compositing": False,
        "samples": samples,
        "frames": frames,
        "start_task": 1,
        "output_format": output_format,
        "crops": crops_render_data
    }

    return crops, params


# todo review: this function shouldn't know anything about the
#  raw verification's existence. The whole file shouldn't know about it.
# todo review: clarify what are "results" - find better name
# todo review: clarify what are "crops" (images? paths to images? instances of
#  Crop class?) - find better name
# todo review: "subtask_file_paths" suggests this function operates on more than
#  one subtask, find better name
def make_verdict(subtask_file_paths, crops, results, use_raw_verification):
    verdict = True

    for crop_data in results:
        crop = get_crop_with_id(crop_data['crop']['id'], crops)

        # todo review: clean it up
        # TODO: Used with the old generate_single_random_crop_data
        left, top = crop.get_relative_top_left()
        left, top = crop.pixel_region.left, crop.pixel_region.top
        print('borders_x: ', crop_data['crop']['borders_x'])
        print('borders_y: ', crop_data['crop']['borders_y'])
        print("left: " + str(left))
        print("top: " + str(top))

        for crop, subtask in zip(crop_data['results'], subtask_file_paths):
            crop_path = os.path.join(OUTPUT_DIR, crop)
            if not use_raw_verification:
                results_path = calculate_metrics(
                    crop_path,
                    subtask,
                    left, top,
                    metrics_output_filename=os.path.join(
                        OUTPUT_DIR,
                        crop_data['crop']['outfilebasename'] + "metrics.txt")
                    )
            else:
                results_path = get_raw_verification(
                    crop_path,
                    subtask,
                    left,
                    top,
                    metrics_output_filename=os.path.join(
                        OUTPUT_DIR,
                        crop_data['crop']['outfilebasename'] + "metrics.txt"
                    ),
                )
            print("results_path: ", results_path)
            with open(results_path, 'r') as f:
                data = json.load(f)
            if data['Label'] != "TRUE":
                verdict = False

    with open(os.path.join(OUTPUT_DIR, 'verdict.json'), 'w') as f:
        json.dump({'verdict': verdict}, f)


def verify(  # pylint: disable=too-many-arguments
        subtask_file_paths,
        subtask_border,
        scene_file_path,
        resolution,
        samples,
        frames,
        output_format,
        crops_count=3,
        crops_borders=None,
        use_raw_verification=False,
):
    """
    Function will verify image with crops rendered from given blender
    scene file.

    subtask_file_paths - path (or paths if there was more than one frame)
                         to image file, that will be compared against crops
    subtask_border - [left, top, right, bottom] float decimal values
                     representing image localization in whole blender scene
    scene_file_path - path to blender scene file
    resolution - resolution at which given subtask was rendered
                 (crop will be rendered with exactly same parameters)
    samples - samples at which given subtask was rendered
    frames - number of frames that are present in subtasks
    output_format - output format of rendered crops
    crops_count - number of randomly generated crops, (default 3)
    crops_borders - list of [left, top, right, bottom] float decimal
                    values lists, representing crops borders
                    those will be used instead of random crops, if present.
    """
    mounted_paths = dict()
    mounted_paths["WORK_DIR"] = WORK_DIR
    mounted_paths["OUTPUT_DIR"] = OUTPUT_DIR

    # todo review: clarify what "crops" are, unless it becomes obvious after
    #  renaming "prepare_params"
    # todo review: clarify what "params" are, unless it becomes obvious after
    #  renaming "prepare_params"
    crops, params = prepare_params(subtask_border, scene_file_path, resolution,
                                   samples, frames, output_format, crops_count,
                                   crops_borders)

    results = blender.render(params, mounted_paths)

    print(results)

    make_verdict(subtask_file_paths, crops, results, use_raw_verification)
