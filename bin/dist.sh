#!/bin/sh
distdir="$(dirname "$0")/../dist"
mkdir -p "$distdir"
cd "$distdir"
for m in classic_ddr itg modern_ddr
do
subdir="stepml-ratings-$m"
echo "[$m]"
mkdir -p "$subdir"
cp "../data/$m/output/"* "$subdir/"
done
zip -r9y "stepml-ratings-$(date '+%Y%m%d').zip" */
