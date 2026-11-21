#!/bin/bash
# 학생 기도 생성 환경 준비: 음성 모델(Kokoro), 한글 글꼴. 이미 있으면 건너뜀.
set -e
D=${PRAYER_ASSETS:-/home/claude/opic_assets}; mkdir -p "$D"; cd "$D"
pip install -q kokoro-onnx soundfile --break-system-packages 2>/dev/null || pip install -q kokoro-onnx soundfile
[ -f kokoro-v1.0.onnx ] || curl -sSLf -o kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -f voices-v1.0.bin ] || curl -sSLf -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
ls /usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc >/dev/null 2>&1 || (apt-get install -y -q fonts-noto-cjk || (apt-get update -q && apt-get install -y -q fonts-noto-cjk))
which ffmpeg >/dev/null || (apt-get install -y -q ffmpeg || (apt-get update -q && apt-get install -y -q ffmpeg))
node -e "require('playwright')" && echo "준비 완료: $D"
