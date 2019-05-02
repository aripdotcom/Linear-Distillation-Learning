import os
import sys
import glob
from functools import partial

import numpy as np
from PIL import Image

import torch
from torchvision.transforms import ToTensor, Resize
from torchvision import transforms
from torchnet.dataset import ListDataset, TransformDataset
from torchnet.transform import compose


OMNIGLOT_DATA_DIR  = os.path.join('data/omniglot')
OMNIGLOT_CACHE = { }


# def convert_dict(k, v):
#     return {k:v}


class CudaTransform(object):
    def __init__(self):
        pass

    def __call__(self, data):
        for k,v in data.items():
            if hasattr(v, 'cuda'):
                data[k] = v.cuda()

        return data


class EpisodicBatchSampler(object):
    def __init__(self, n_classes, n_way, n_episodes):
        self.n_classes = n_classes
        self.n_way = n_way
        self.n_episodes = n_episodes

    def __len__(self):
        return self.n_episodes

    def __iter__(self):
        for i in range(self.n_episodes):
            yield torch.randperm(self.n_classes)[:self.n_way]


def load_image_path(path):
    return Image.open(path)


def load_pil_image(path):
    img = Image.open(path)
    return img


def scale_pil_image(img, size=(28,28)):
    return img.resize(size)


def pil2tensor(img):
    return torch.from_numpy(np.array(img, np.float32))


def convert_tensor(img):
    return 1.0 - torch.from_numpy(np.array(img, np.float32, copy=False)).transpose(0, 1).contiguous().view(1, img.size[0], img.size[1])


def rotate_image(rot, img):
    return img.rotate(rot)


def scale_image(height, width, img):
    return img.resize((height, width))


def load_class_images(class_name):
    if class_name not in OMNIGLOT_CACHE:
        alphabet, character, rot = class_name.split('/')
        image_dir = os.path.join(OMNIGLOT_DATA_DIR, 'data', alphabet, character)

        class_images = sorted(glob.glob(os.path.join(image_dir, '*.png')))
        if len(class_images) == 0:
            raise Exception("No images found for omniglot class {} at {}. Did you run download_omniglot.sh first?".format(class_name, image_dir))

        image_ds = TransformDataset(ListDataset(class_images),
                                    compose([load_image_path,
                                             partial(rotate_image, float(rot[3:])),
                                             partial(scale_image, 28, 28),
                                             convert_tensor]))

        loader = torch.utils.data.DataLoader(image_ds, batch_size=len(image_ds), shuffle=False)

        for sample in loader:
            OMNIGLOT_CACHE[class_name] = sample
            break

    return {'class': class_name, 'data': OMNIGLOT_CACHE[class_name]}


def extract_episode(n_support, n_query, d):
    # data: N x C x H x W
    n_examples = d['data'].size(0)

    if n_query == -1:
        n_query = n_examples - n_support

    example_inds = torch.randperm(n_examples)[:(n_support+n_query)]
    support_inds = example_inds[:n_support]
    query_inds = example_inds[n_support:]

    xs = d['data'][support_inds]
    xq = d['data'][query_inds]

    return {
        'class': d['class'],
        'xs': xs,
        'xq': xq
    }


def get_episodic_loader(way, train_shot, test_shot, split='train', add_rotations=True):
    """
    Return data loader of single episode.

    Args:
        way (int): number of different classes in data
        train_shot (int): number of samples per class in train
        test_shot (int): number of samples per class in test
        split (str): name of the split in 'vinyals' environment

    Returns (torch.utils.data.DataLoader): torch data loader

    """
    transforms = [load_class_images,
                  partial(extract_episode, train_shot, test_shot)]
    transforms = compose(transforms)

    split_dir = os.path.join(OMNIGLOT_DATA_DIR, 'splits')
    with open(os.path.join(split_dir, "{:s}.txt".format(split)), 'r') as f:
        alphabet_names = f.readlines()

    # Augment dataset with new classes via rotations
    class_names = []
    if add_rotations:
        rotates = ["000", "090", "180", "270"]
    else:
        rotates = ["000"]

    # Class name is alphabet/character/rotate degree
    # Total number of classes: alphabet * character * rotate_degree
    for alph in alphabet_names:
        character_paths = glob.glob(os.path.join(OMNIGLOT_DATA_DIR, "data", alph, "*"))
        for ch_path in character_paths:
            ch_name = ch_path[ch_path.rfind('/')+1:]
            class_names += [f"{alph}/{ch_name}/rot{rot}" for rot in rotates]

    ds = TransformDataset(ListDataset(class_names), transforms)

    sampler = EpisodicBatchSampler(len(ds), way, 1)
    loader = torch.utils.data.DataLoader(ds, batch_sampler=sampler, num_workers=0)
    return loader


def get_data_loader(split):
    image_dir = os.path.join(OMNIGLOT_DATA_DIR, 'data')
    images_files = glob.glob(os.path.join(image_dir, "*/*/*.png"))

    image_ds = TransformDataset(ListDataset(images_files),
                                compose([load_pil_image,
                                         scale_pil_image,
                                         #pil2tensor,
                                         transforms.ToTensor(),
                                         #transforms.Normalize((0.5,), (0.5,))
                                         ]))

    loader = torch.utils.data.DataLoader(image_ds, batch_size=32,
                                         shuffle=True)
    return loader