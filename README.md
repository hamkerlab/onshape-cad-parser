# Onshape-CAD-Parser TU-Chemnitz Version

This is a currently working branch of the [Onshape-CAD-Parser](https://github.com/rundiwu/onshape-cad-parser) developed by Rundi Wu. It drastically reduces API calls and avoids a critical bug in the OnShape API that caused the old version to stop functioning by loading from an offline copy of the ABC dataset.

## Changes

- Reduced the number of calls to the OnShape API
    - `get_features()` is no longer called. The ofs data is instead retrieved locally
    - The information retrieved by `eval_curve_midpoint` is now included in `eval_sketch_topology_by_adjacency`
    - Unit conversion by `expr2meter` is now done locally
    - Removed unused functions from `myclient.py` for clarity
- Added .gitignore

## Dependencies

Follow the regular installation instructions [here](https://github.com/rundiwu/onshape-cad-parser).

Additionally, you need to download the ABC dataset *in the ofs format* by following the instructions [here](https://deep-geometry.github.io/abc-dataset/). Create a folder named `files` in the project directory and extract the dataset there. The resulting folder structure should look something like this:
> {project directory}/files/00009999/{file name}.yml