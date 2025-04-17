#!/usr/bin/env python
# coding: utf-8
import cv2
import numpy as np
from tqdm import tqdm
import os
import subprocess
import shutil
from pathlib import Path

def ensure_directory_exists(file_path):
    """确保文件所在目录存在"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
def validate_paths(video_path, image_path, output_path):
    """验证输入输出路径"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    ensure_directory_exists(output_path)
    
def create_temp_directory(output_path):
    """创建临时文件目录"""
    temp_dir = os.path.join(os.path.dirname(output_path), '.temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def cleanup_temp_files(temp_files):
    """清理临时文件"""
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"清理临时文件失败 {file}: {str(e)}")

def overlay_image_alpha(img, img_overlay, opacity):
    """将带 alpha 通道的图片叠加到背景图片上"""
    # 确保图像是浮点型
    img = img.astype(float)
    img_overlay = img_overlay.astype(float)

    # 提取 alpha 通道并归一化
    alpha = (img_overlay[:, :, 3] / 255.0) * opacity
    alpha_inv = 1.0 - alpha

    # 将 alpha 通道扩展为三通道
    alpha = cv2.merge([alpha, alpha, alpha])
    alpha_inv = cv2.merge([alpha_inv, alpha_inv, alpha_inv])

    # 进行融合
    img = alpha * img_overlay[:, :, :3] + alpha_inv * img

    return img.astype(np.uint8)

def run_ffmpeg_quiet(*args):
    """静默运行 FFmpeg 命令"""
    try:
        subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 错误: {e.stderr.decode()}")
        raise

def overlay_image_on_video(
    video_path,
    image_path,
    output_path,
    start_time,
    end_time,
    opacity=0.9,
    padding=20,
    fade_duration=0.5,
    quality='high'
):
    temp_files = []
    temp_dir = None
    
    try:
        # 验证路径
        validate_paths(video_path, image_path, output_path)
        
        # 创建临时目录
        temp_dir = create_temp_directory(output_path)
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")

        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 读取并处理叠加图像
        overlay_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if overlay_image is None:
            raise ValueError("无法读取图片文件")

        # 处理 alpha 通道
        if overlay_image.shape[2] == 3:
            alpha_channel = np.ones((overlay_image.shape[0], overlay_image.shape[1], 1), dtype='uint8') * 255
            overlay_image = np.concatenate((overlay_image, alpha_channel), axis=2)

        # 计算图片尺寸
        img_height, img_width = overlay_image.shape[:2]
        img_aspect_ratio = img_width / img_height
        video_aspect_ratio = video_width / video_height

        # 计算图片的目标尺寸
        if img_aspect_ratio > video_aspect_ratio:
            resized_width = int(video_width - 2 * padding)
            resized_height = int(resized_width / img_aspect_ratio)
        else:
            resized_height = int(video_height / 2 - 2 * padding)
            resized_width = int(resized_height * img_aspect_ratio)

        overlay_image = cv2.resize(overlay_image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

        # 计算位置
        x_pos = int((video_width - resized_width) / 2)
        y_pos = padding

        if video_width / video_height > 16 / 9:
            y_pos = int((video_height - resized_height) / 2)

        # 创建透明图层
        static_overlay = np.zeros((video_height, video_width, 4), dtype='uint8')
        static_overlay[y_pos:y_pos+resized_height, x_pos:x_pos+resized_width] = overlay_image

        # 设置临时文件路径
        temp_video = os.path.join(temp_dir, "temp_video")
        temp_files.append(temp_video)

        # 尝试不同的编码器
        codecs = [
            ('XVID', 'avi'),
            ('MJPG', 'avi'),
            ('mp4v', 'mp4'),
        ]
        
        out = None
        for codec, ext in codecs:
            try:
                temp_video_path = f"{temp_video}.{ext}"
                temp_files.append(temp_video_path)
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(temp_video_path, fourcc, fps, (video_width, video_height))
                if out.isOpened():
                    print(f"使用 {codec} 编码器")
                    break
            except Exception as e:
                print(f"编码器 {codec} 失败: {str(e)}")
                if out is not None:
                    out.release()

        if out is None or not out.isOpened():
            raise ValueError("无法创建输出视频文件")

        # 计算帧范围
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        fade_frames = int(fade_duration * fps)

        # 处理视频帧
        for frame_idx in tqdm(range(frame_count), desc="处理视频"):
            ret, frame = cap.read()
            if not ret:
                break

            if start_frame <= frame_idx <= end_frame:
                if frame_idx < start_frame + fade_frames:
                    fade_opacity = opacity * (frame_idx - start_frame) / fade_frames
                elif frame_idx > end_frame - fade_frames:
                    fade_opacity = opacity * (end_frame - frame_idx) / fade_frames
                else:
                    fade_opacity = opacity

                frame = overlay_image_alpha(frame, static_overlay, fade_opacity)

            out.write(frame)

        # 释放资源
        cap.release()
        out.release()
        cv2.destroyAllWindows()

        # 处理输出视频
        try:
            # 设置质量参数
            crf = '18' if quality == 'high' else '23' if quality == 'medium' else '28'
            preset = 'slow' if quality == 'high' else 'medium' if quality == 'medium' else 'fast'
            
            # 直接处理视频（不包含音频）
            run_ffmpeg_quiet(
                'ffmpeg', '-i', temp_video_path,
                '-c:v', 'libx264',
                '-preset', preset,
                '-crf', crf,
                '-y', output_path
            )
            return output_path

        except Exception as e:
            print(f"FFmpeg 处理失败，使用原始输出: {str(e)}")
            shutil.copy2(temp_video_path, output_path)

    except Exception as e:
        print(f"处理失败: {str(e)}")
        raise

    finally:
        # 清理临时文件和目录
        cleanup_temp_files(temp_files)
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时目录失败: {str(e)}")