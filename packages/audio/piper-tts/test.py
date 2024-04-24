#!/usr/bin/env python3
import os
import time
import wave
import onnxruntime

from piper import PiperVoice
from piper.download import ensure_voice_exists, find_voice, get_voices

DEFAULT_PROMPT="""A rainbow is a meteorological phenomenon that is caused by reflection, refraction and dispersion of light in water droplets resulting in a spectrum of light appearing in the sky.
It takes the form of a multi-colored circular arc.
Rainbows caused by sunlight always appear in the section of sky directly opposite the Sun.
With tenure, Suzie’d have all the more leisure for yachting, but her publications are no good.
Shaw, those twelve beige hooks are joined if I patch a young, gooey mouth.
Are those shy Eurasian footwear, cowboy chaps, or jolly earthmoving headgear?
The beige hue on the waters of the loch impressed all, including the French queen, before she heard that symphony again, just as young Arthur wanted.
"""

def main(model='en_US-lessac-high', config=None, cache=os.environ.get('PIPER_CACHE'),
         speaker=0, length_scale=1.0, noise_scale=0.667, noise_w=0.8, sentence_silence=0.2,
         prompt=DEFAULT_PROMPT, output='/dev/null', use_cuda=True, runs=5, **kwargs):

    if not os.path.isfile(os.path.join(cache, model)):
        # Download voice info
        try:
            voices_info = get_voices(cache, update_voices=True)
        except Exception as error:
            print(f"Failed to download Piper voice list  ({error})")
            voices_info = get_voices(cache)
            
        # Resolve aliases for backwards compatibility with old voice names
        aliases_info = {}
        for voice_info in voices_info.values():
            for voice_alias in voice_info.get("aliases", []):
                aliases_info[voice_alias] = {"_is_alias": True, **voice_info}

        voices_info.update(aliases_info)
        ensure_voice_exists(model, cache, cache, voices_info)
        model, config = find_voice(model, [cache])

    # Load model
    print(f"Loading {model}")
    
    voice = PiperVoice.load(model, config_path=config, use_cuda=True)
    
    synthesize_args = {
        "speaker_id": speaker,
        "length_scale": length_scale,
        "noise_scale": noise_scale,
        "noise_w": noise_w,
        "sentence_silence": sentence_silence,
    }

    # Run benchmarking iterations
    for run in range(runs):
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            start = time.perf_counter()
            voice.synthesize(prompt, wav_file, **synthesize_args)
            end = time.perf_counter()

            inference_duration = end - start

            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            audio_duration = frames / float(rate)

        print(f"Piper TTS model:    {os.path.splitext(os.path.basename(model))[0]}")
        print(f"Output saved to:    {output}")
        print(f"Inference duration: {inference_duration:.3f} sec")
        print(f"Audio duration:     {audio_duration:.3f} sec")
        print(f"Realtime factor:    {inference_duration/audio_duration:.3f}")
        print(f"Inverse RTF (RTFX): {audio_duration/inference_duration:.3f}\n")
    
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('--model', type=str, default='en_US-lessac-high', help="model path or name to download")
    parser.add_argument('--config', type=str, default=None, help="path to the model's json config (if unspecified, will be inferred from --model)")
    parser.add_argument('--cache', type=str, default=os.environ.get('PIPER_CACHE'), help="the location to save downloaded models")
    
    parser.add_argument('--speaker', type=int, default=0, help="the speaker ID from the voice to use")
    parser.add_argument('--length-scale', type=float, default=1.0, help="speaking speed")
    parser.add_argument('--noise-scale', type=float, default=0.667, help="noise added to the generator")
    parser.add_argument('--noise-w', type=float, default=0.8, help="phoneme width variation")
    parser.add_argument('--sentence-silence', type=float, default=0.2, help="seconds of silence after each sentence")
    
    parser.add_argument('--prompt', type=str, default=None, help="the test prompt to generate (will be set to a default prompt if left none)")
    parser.add_argument('--output', type=str, default=None, help="path to output audio wav file to save (will be /data/tts/piper-$MODEL.wav by default)")
    parser.add_argument('--runs', type=int, default=5, help="the number of benchmarking iterations to run")
    parser.add_argument('--disable-cuda', action='store_false', dest='use_cuda', help="disable CUDA and use CPU for inference instead")
    parser.add_argument('--verbose', action='store_true', help="enable onnxruntime debug logging")
    
    args = parser.parse_args()
         
    if args.verbose:
        onnxruntime.set_default_logger_severity(0)
 
    if not args.prompt:
        args.prompt = DEFAULT_PROMPT
        
    if not args.output:
        args.output = f"/data/audio/tts/piper-{os.path.splitext(os.path.basename(args.model))[0]}.wav"

    print(args)
    
    main(**vars(args))
