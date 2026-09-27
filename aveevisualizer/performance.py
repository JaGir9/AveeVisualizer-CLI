import os, platform, shutil, subprocess

def _encoder_list():
    try:
        p=subprocess.run(['ffmpeg','-hide_banner','-encoders'],capture_output=True,text=True,timeout=8)
        return p.stdout+p.stderr
    except Exception: return ''

def _probe_encoder(name):
    try:
        p=subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=size=64x64:rate=1','-frames:v','1','-c:v',name,'-f','null','-'],capture_output=True,timeout=8)
        return p.returncode==0
    except Exception: return False

def detect_profile():
    cores=os.cpu_count() or 2
    enc=_encoder_list()
    candidates=[('h264_nvenc','NVIDIA NVENC'),('h264_qsv','Intel Quick Sync'),('h264_amf','AMD AMF'),('h264_videotoolbox','Apple VideoToolbox')]
    encoder='libx264'; label='CPU / libx264'
    for name,title in candidates:
        if name in enc and _probe_encoder(name):
            encoder,label=name,title; break
    if encoder!='libx264': speed='fast'
    elif cores>=16: speed='veryfast'
    elif cores>=8: speed='veryfast'
    elif cores>=4: speed='superfast'
    else: speed='ultrafast'
    return {'os':platform.system(),'cpu':platform.processor() or platform.machine(),'cores':cores,'encoder':encoder,'encoder_label':label,'preset':speed}

def describe(p):
    return f"{p['os']} | {p['cores']} logical CPU | Encoder: {p['encoder_label']} | Auto preset: {p['preset']}"
