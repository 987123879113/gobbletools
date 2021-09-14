#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: Waifu2x Caffe Driver
Author: K4YT3X
Date Created: Feb 24, 2018
Last Modified: February 8, 2019

Description: This class controls waifu2x
engine

Version 2.0.5
"""

import os
import subprocess
import threading


class Waifu2xCaffe:
    """This class communicates with waifu2x cui engine

    An object will be created for this class, containing information
    about the binary address and the processing method. When being called
    by the main program, other detailed information will be passed to
    the upscale function.
    """

    def __init__(self, waifu2x_path, method, model_type):
        self.waifu2x_path = waifu2x_path
        self.method = method
        self.model_type = model_type

    def upscale(self, folderin, folderout, ratio, noise_level=3, batch_size=16, gpu_device=0):
        """This is the core function for WAIFU2X class

        Arguments:
            folderin {string} -- source folder path
            folderout {string} -- output folder path
            width {int} -- output video width
            height {int} -- output video height
        """

        # Create string for execution
        execute = '\"{}\" -i \"{}\" -o {} --crop_size 64 --scale_ratio {} --process {} --noise_level {} --mode noise_scale --input_extension_list png --model_dir "{}" --gpu {}  --output_quality 100 --batch_size {} --tta 0'.format(self.waifu2x_path, folderin, folderout, ratio, self.method, noise_level, os.path.join(os.path.dirname(self.waifu2x_path), "models", self.model_type), gpu_device, batch_size)
        print(execute)
        subprocess.call(execute)
