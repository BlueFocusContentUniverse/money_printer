from pydub import AudioSegment
from services.material_process.sound_effect_analyzer import SoundEffectResult
import os
import io

class SoundEffectProcessor:
    def process(self, tts_audio_path: str, sound_effect: SoundEffectResult) -> str:
        """
        处理音频,在指定位置插入音效
        Args:
            tts_audio_path: TTS 音频文件路径
            sound_effect: 音效分析结果
        Returns:
            处理后的音频文件路径(绝对路径)
        """
        if sound_effect is None:
            return os.path.abspath(tts_audio_path)
            
        try:
            # 1. 加载音频文件
            tts_audio = AudioSegment.from_file(tts_audio_path, format="wav")
            if len(tts_audio) == 0:
                # 如果长度为0，尝试重新加载
                with open(tts_audio_path, 'rb') as f:
                    audio_data = f.read()
                tts_audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
                
            # print(f"TTS音频长度: {len(tts_audio)}ms")
            # print(f"音频通道数: {tts_audio.channels}")
            # print(f"音频采样率: {tts_audio.frame_rate}")
            # print(f"音频采样宽度: {tts_audio.sample_width}")
            sound_effect_audio = AudioSegment.from_file(sound_effect.sound_file)
            # print(f"音效音频长度: {len(sound_effect_audio)}ms")
            # 2. 统一音频参数
            sound_effect_audio = self._match_audio_params(sound_effect_audio, tts_audio)
            # print(f"统一音频参数后的音效音频长度: {len(sound_effect_audio)}ms")
            # 3. 调整音效音量
            sound_effect_audio = sound_effect_audio - 9  # 降低 9dB
            # print(f"调整音量后的音效音频长度: {len(sound_effect_audio)}ms")
            # 4. 计算插入位置(毫秒)
            insert_position_ms = int((sound_effect.start_time + 0.1) * 1000)
            # print(f"插入位置: {insert_position_ms}ms")
            # 5. 混合音频
            combined_audio = self._mix_audio(tts_audio, sound_effect_audio, insert_position_ms)
            # print(f"混合音频长度: {len(combined_audio)}ms")
            # 6. 保存处理后的文件
            output_path = os.path.abspath(tts_audio_path.replace('.wav', '_with_effect.wav'))
            combined_audio.export(output_path, format='wav')
            print(f"处理后的音频文件路径: {output_path}")
            return output_path
            
        except Exception as e:
            raise Exception(f"处理音效失败: {e.__class__.__name__}: {str(e)}")

    def _match_audio_params(self, sound_effect_audio, tts_audio):
        """
        统一音频参数
        Args:
            sound_effect_audio: 音效音频
            tts_audio: TTS 音频
        Returns:
            统一参数后的音效音频
        """

        sound_effect_audio = sound_effect_audio.set_frame_rate(tts_audio.frame_rate)
        sound_effect_audio = sound_effect_audio.set_channels(tts_audio.channels)
        sound_effect_audio = sound_effect_audio.set_sample_width(tts_audio.sample_width)
        return sound_effect_audio

    def _mix_audio(self, tts_audio, sound_effect_audio, insert_position_ms):
        if insert_position_ms <= 0:
        # 音效在文本前面
            # print(f"音效在文本前面")
            padded_tts_audio = AudioSegment.silent(duration=300) + tts_audio
            combined_audio = padded_tts_audio.overlay(sound_effect_audio, position=0)
        else:
            # 音效在文本中间
            # print(f"音效在文本中间")
            combined_audio = tts_audio.overlay(sound_effect_audio, position=insert_position_ms)
        # print(f"混合音频长度: {len(combined_audio)}ms")
        return combined_audio