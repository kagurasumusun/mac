import re

with open("src/actool_linux/carwriter.py", "r") as f:
    cw_content = f.read()

# build_assets_car returns bytes, which is widely used, but let's change it internally.
new_car_build = '''    def build_assets_car_multilevel(assets: list[AssetRendition], *, platform: str, target: str, thinning_arguments: str = "", coreui_profile: "CoreUIProfile | str | None" = None) -> bytes:
        return _build_assets_car_multilevel(assets, platform=platform, target=target, thinning_arguments=thinning_arguments, coreui_profile=coreui_profile)'''
# Instead of replacing build_assets_car (too long), let's just replace write_bytes with a stream loop for the final return. Actually, carwriter `build_assets_car` uses BOMWriter.build(), which is returned as bytes.
# So optimizing BOMWriter is the most effective.
