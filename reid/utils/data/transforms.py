from __future__ import absolute_import

from torchvision.transforms import *
from PIL import Image, ImageOps
from lz import *


class RectScale(object):
    def __init__(self, height, width, interpolation=Image.BILINEAR):
        self.height = height
        self.width = width
        self.interpolation = interpolation

    def __call__(self, img):
        if isinstance(img, np.ndarray):
            type(img)
            return img
        w, h = img.size
        if h == self.height and w == self.width:
            return img

        ## todo
        ## way 1: keep ar resize crop big to small
        # ratio_w = self.width / w
        # ratio_h = self.height / h
        # ratio = max(ratio_h, ratio_w)
        # target_size = (int(w * ratio), int(h * ratio))
        # img = img.resize(target_size, self.interpolation)  # resize if width height
        # img = CenterCrop((self.height, self.width))(img)
        # # pytorch transofrm Resize is height width
        # # img is width height

        ## way 2: direct resize
        img = img.resize((self.width, self.height), self.interpolation)

        ## way 3: keep ar resize padding  small to big
        # max_long_edge = max(self.height, self.width)
        # max_short_edge = min(self.height, self.width)
        # scale = min(
        #     float(max_long_edge) / max(h, w), float(max_short_edge) / min(h, w))
        # new_size = cvb.scale_size((w, h), scale)
        # img = img.resize(new_size, self.interpolation)
        # w_new = self.width - new_size[0]
        # h_new = self.height - new_size[1]
        # w_new_2 = w_new // 2
        # h_new_2 = h_new // 2
        # img = ImageOps.expand(img, (w_new_2, h_new_2, w_new - w_new_2, h_new - h_new_2))

        return img


# todo more aug, try random erasing

class RandomCropFlip1(object):
    """
    With a probability, first increase image size to (1 + 1/8), and then perform random crop.
    Args:
    - height (int): target image height.
    - width (int): target image width.
    - p (float): probability of performing this transformation. Default: 0.5.
    """

    def __init__(self, height, width, interpolation=Image.BILINEAR, p=0.5, **kwargs):
        self.height = height
        self.width = width
        self.p = p
        self.interpolation = interpolation
        self.new_width, self.new_height = int(round(self.width * 1.125)), int(round(self.height * 1.125))
        self.scale = RectScale(self.new_height, self.new_width,
                               interpolation=self.interpolation)
        self.scale_ori = RectScale(self.height, self.width,
                                   interpolation=self.interpolation)

    def __call__(self, img):
        """
        Args:
        - img (PIL Image): Image to be cropped.
        """
        if random.uniform(0, 1) > self.p:
            return self.scale_ori(img)

        resized_img = self.scale(img)
        x_maxrange = self.new_width - self.width
        y_maxrange = self.new_height - self.height
        x1 = int(round(random.uniform(0, x_maxrange)))
        y1 = int(round(random.uniform(0, y_maxrange)))
        croped_img = resized_img.crop((x1, y1, x1 + self.width, y1 + self.height))
        return croped_img


class RandomCropFlip(object):
    def __init__(self, height, width, interpolation=Image.BILINEAR, area=(.85, 1),
                 aspect=(1.5, 3)):  # 0.64, 1 # .85, 1  # 2, 3  # todo
        self.height = height
        self.width = width
        self.interpolation = interpolation
        self.aspect = aspect
        self.area = area
        self.scale = RectScale(self.height, self.width,
                               interpolation=self.interpolation)

    def __call__(self, img):
        if random.random() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

        for attempt in range(999):
            area = img.size[0] * img.size[1]
            target_area = random.uniform(*self.area) * area
            aspect_ratio = random.uniform(*self.aspect)

            # this assume height > width
            if img.size[0] < img.size[1]:
                h = int(round(math.sqrt(target_area * aspect_ratio)))
                w = int(round(math.sqrt(target_area / aspect_ratio)))
            else:
                w = int(round(math.sqrt(target_area * aspect_ratio)))
                h = int(round(math.sqrt(target_area / aspect_ratio)))
            if w <= img.size[0] and h <= img.size[1]:  # img is width height
                # print('ok', w, h)
                x1 = random.randint(0, img.size[0] - w)
                y1 = random.randint(0, img.size[1] - h)

                img = img.crop((x1, y1, x1 + w, y1 + h))
                assert (img.size == (w, h))
                return self.scale(img)
        # Fallback
        return self.scale(img)


class RandomErasing(object):
    """ Randomly selects a rectangle region in an image and erases its pixels.
        'Random Erasing Data Augmentation' by Zhong et al.
        See https://arxiv.org/pdf/1708.04896.pdf
    Args:
         probability: The probability that the Random Erasing operation will be performed.
         sl: Minimum proportion of erased area against input image.
         sh: Maximum proportion of erased area against input image.
         r1: Minimum aspect ratio of erased area.
         mean: Erasing value.
    """

    def __init__(self, probability=0.5, sl=0.02, sh=0.4, r1=0.3, mean=[0.4914, 0.4822, 0.4465]):
        self.probability = probability
        self.mean = mean
        self.sl = sl
        self.sh = sh
        self.r1 = r1

    def __call__(self, img):

        if random.uniform(0, 1) > self.probability:
            return img

        for attempt in range(100):
            area = img.size()[1] * img.size()[2]

            target_area = random.uniform(self.sl, self.sh) * area
            aspect_ratio = random.uniform(self.r1, 1 / self.r1)

            h = int(round(math.sqrt(target_area * aspect_ratio)))
            w = int(round(math.sqrt(target_area / aspect_ratio)))

            if w < img.size()[2] and h < img.size()[1]:
                x1 = random.randint(0, img.size()[1] - h)
                y1 = random.randint(0, img.size()[2] - w)
                if img.size()[0] == 3:
                    img[0, x1:x1 + h, y1:y1 + w] = self.mean[0]
                    img[1, x1:x1 + h, y1:y1 + w] = self.mean[1]
                    img[2, x1:x1 + h, y1:y1 + w] = self.mean[2]
                else:
                    img[0, x1:x1 + h, y1:y1 + w] = self.mean[0]
                return img

        return img


class RandomSizedRectCrop(object):
    def __init__(self, height, width, interpolation=Image.BILINEAR):
        self.height = height
        self.width = width
        self.interpolation = interpolation

    def __call__(self, img):
        for attempt in range(10):
            area = img.size[0] * img.size[1]
            target_area = random.uniform(0.85, 1.0) * area
            aspect_ratio = random.uniform(2, 3)

            h = int(round(math.sqrt(target_area * aspect_ratio)))
            w = int(round(math.sqrt(target_area / aspect_ratio)))

            if w <= img.size[0] and h <= img.size[1]:
                x1 = random.randint(0, img.size[0] - w)
                y1 = random.randint(0, img.size[1] - h)

                img = img.crop((x1, y1, x1 + w, y1 + h))
                assert (img.size == (w, h))
                return img.resize((self.width, self.height), self.interpolation)

        # Fallback
        scale = RectScale(self.height, self.width,
                          interpolation=self.interpolation)
        return scale(img)
