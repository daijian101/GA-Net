import os

from cavass.ops import read_cavass_file
from jbag.io import save_json, read_json
from tqdm import tqdm
from jbag.config import load_config
from jbag.parallel_processing import execute


def convert_im0(study, target_study_file):
    if not os.path.exists(target_study_file):
        im0_file = os.path.join(im0_path, f'{study}.IM0')
        im0_data = read_cavass_file(im0_file)
        image_data = {'data': im0_data,
                      'study': study}
        save_json(target_study_file, image_data)


def convert_bim(study, label, target_label_file):
    if not os.path.exists(target_label_file):
        label_file = os.path.join(image_root_path, label, f'{study}.BIM')
        label_data = read_cavass_file(label_file)
        data = {'data': label_data, 'study': study, 'class': label}
        save_json(target_label_file, data)

if __name__ == '__main__':
    data_path = '/data1/dj/data/bca/'

    image_root_path = os.path.join(data_path, 'cavass_data')
    im0_path = os.path.join(image_root_path, 'images')

    ct_saved_image_path = os.path.join(data_path, 'json/volume/images')
    label_saved_root_path = os.path.join(data_path, 'json/volume')

    labels = ['SAT']

    cfg = load_config('../../cfgs/training/GA-Net_SAT.toml')
    dataset_properties = read_json(cfg.dataset.dataset_property_file)
    cts = dataset_properties['val_set'] + dataset_properties['test_set']

    p = []
    for study in cts:
        ct_saved_file_path = os.path.join(ct_saved_image_path, f'{study}.json')
        p.append((study, ct_saved_file_path))

    execute(convert_im0, 32, p)

    if labels:
        p = []
        for study in cts:
            for label in labels:
                label_saved_file_path = os.path.join(label_saved_root_path, label, f'{study}.json')
                p.append((study, label,  label_saved_file_path))

        execute(convert_bim, 32, p)
