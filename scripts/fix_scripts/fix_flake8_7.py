import subprocess

files = [
    "src/actool_linux/appicons.py", "src/actool_linux/atlas.py", "src/actool_linux/atlas_geometry.py",
    "src/actool_linux/bom.py", "src/actool_linux/bomwriter.py", "src/actool_linux/capabilities.py",
    "src/actool_linux/car.py", "src/actool_linux/carinfo.py", "src/actool_linux/carwriter.py",
    "src/actool_linux/cbck.py", "src/actool_linux/cbck_complete.py", "src/actool_linux/cli.py",
    "src/actool_linux/compiler.py", "src/actool_linux/coreui.py", "src/actool_linux/csi.py",
    "src/actool_linux/diagnostics.py", "src/actool_linux/dmp2mini.py", "src/actool_linux/facet_hash_lookup.py",
    "src/actool_linux/iconstack.py", "src/actool_linux/imagestack.py", "src/actool_linux/legacy_coreui_features.py",
    "src/actool_linux/lzfse_compat.py", "src/actool_linux/lzfse_optimized.py", "src/actool_linux/model.py",
    "src/actool_linux/multi_database.py", "src/actool_linux/packed.py", "src/actool_linux/paletteimg.py",
    "src/actool_linux/pdfcar.py", "src/actool_linux/repack.py", "src/actool_linux/solidstack.py",
    "src/actool_linux/texture.py", "src/actool_linux/texture_gradient_stack.py", "src/actool_linux/thinning.py",
    "src/actool_linux/tree.py", "src/actool_linux/zero_code_db.py"
]

subprocess.run(["autopep8", "--in-place", "--max-line-length", "200"] + files)

