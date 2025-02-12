import os
from random import shuffle

import numpy as np
from cavass.ops import read_cavass_file
from jbag.io import save_json
from jbag.log import logger
from jbag.parallel_processing import execute



def split_dataset(all_samples):
    shuffle(all_samples)

    n_training = int(0.6 * len(all_samples))
    n_val = int(0.2 * len(all_samples))

    training_set = all_samples[:n_training]
    val_set = all_samples[n_training:n_training + n_val]

    n_test = len(all_samples) - n_training - n_val
    test_set = all_samples[n_training + n_val:]

    logger.info(f'# training set is {n_training}')
    logger.info(f'# val set is {n_val}')
    logger.info(f'# test set is {n_test}')

    return training_set, val_set, test_set


def collect_study_properties(study, image_file, label_file, n_foreground):
    image_data = read_cavass_file(image_file)
    label_data = read_cavass_file(label_file)
    label_data = label_data.astype(bool)
    foreground_pixels = image_data[label_data]
    rs = np.random.RandomState(seed=1234)
    chosen_foreground_pixels = rs.choice(foreground_pixels, n_foreground, replace=True) if len(
        foreground_pixels) > 0 else []

    foreground_slice_range = np.nonzero(label_data)[2]
    n_slices = image_data.shape[2]
    return study, chosen_foreground_pixels, (np.min(foreground_slice_range), np.max(foreground_slice_range)), n_slices


if __name__ == '__main__':
    dataset_dir = '/data1/dj/data/bca/'
    label = 'SAT'

    # Step 1: split dataset
    label_gt_dir = os.path.join(dataset_dir, 'cavass_data', label)
    all_samples = [each[:-4] for each in os.listdir(label_gt_dir) if each.endswith('BIM')]
    training_set, val_set, test_set = split_dataset(all_samples)

    # Step 2: extract statistical values

    num_foreground_voxels_for_intensity_stats = 10e7
    n_training_samples = len(training_set)
    num_foreground_voxels_per_image = int(num_foreground_voxels_for_intensity_stats / n_training_samples)
    print(f'Number of foreground pixels for each volume: {num_foreground_voxels_per_image}')

    im0_dir = os.path.join(dataset_dir, 'cavass_data', 'images')
    params = []
    for sample in training_set:
        image_file = os.path.join(im0_dir, f'{sample}.IM0')
        label_file = os.path.join(label_gt_dir, f'{sample}.BIM')
        params.append((sample, image_file, label_file, num_foreground_voxels_per_image))

    r = execute(collect_study_properties, 64, params)

    foreground_pixels_lst = []
    study_properties = {}
    for study, foreground_pixels, foreground_slice_range, n_slices in r:
        foreground_pixels_lst.append(foreground_pixels)
        study_properties[study] = {'foreground_slice_range': foreground_slice_range, 'num_slices': n_slices}
    all_chosen_intensities = np.concatenate(foreground_pixels_lst)
    mean = np.mean(all_chosen_intensities)
    std = np.std(all_chosen_intensities)
    percentile_0_5, percentile_99_5 = np.percentile(all_chosen_intensities, [0.5, 99.5])

    dataset_properties = {'training_set': training_set, 'val_set': val_set, 'test_set': test_set,
                          'intensity_mean': mean, 'intensity_std': std,
                          'intensity_0_5_percentile': percentile_0_5, 'intensity_99_5_percentile': percentile_99_5,
                          'study_properties': study_properties}

    dataset_properties_file = os.path.join(dataset_dir, 'dataset', f'{label}_dataset_properties.json')
    save_json(dataset_properties_file, dataset_properties)
