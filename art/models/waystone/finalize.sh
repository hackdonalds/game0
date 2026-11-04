#!/bin/zsh
# Meshy source -> web GLB for the Waystone demo.
# art/models/waystone/finalize.sh <key> <height|length|width> <metres> <texture px> [prep.py options...]
set -e
cd "$(dirname $0)/../../.."
key=$1 axis=$2 size=$3 tex=$4; shift 4
B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
G=node_modules/.bin/gltf-transform
tmp=$(mktemp -d)
$B -b --factory-startup -P art/models/waystone/prep.py -- art/models/waystone/$key.glb $tmp/$key.glb $axis $size "$@" 2>&1 | grep -E "^PREP|Error"
$G optimize $tmp/$key.glb demos/waystone/public/models/$key.glb --compress meshopt --texture-compress webp --texture-size $tex --simplify false --palette false --join false >/dev/null
$B -b --factory-startup -P art/models/waystone/render.py -- demos/waystone/public/models/$key.glb art/models/waystone/$key.review.png 2>&1 | grep -E "^dims|Error" || true
ls -l demos/waystone/public/models/$key.glb | awk '{printf "%s %.2f MB\n", $9, $5/1e6}'
