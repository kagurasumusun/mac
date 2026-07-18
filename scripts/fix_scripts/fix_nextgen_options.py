import re

with open("src_nextgen/actool_linux/compiler.py", "r") as f:
    content = f.read()

# Add optimize field to CompileOptions
new_options = '''@dataclass
class CompileOptions:
    output: Path
    platform: str | None = None
    minimum_deployment_target: str | None = None
    app_icon: str | None = None
    accent_color: str | None = None
    launch_image: str | None = None
    complication: str | None = None
    partial_info_plist: Path | None = None
    warnings: bool = True
    errors: bool = True
    notices: bool = True
    target_devices: tuple[str, ...] = ()
    filter_for_device_model: str | None = None
    filter_for_device_os_version: str | None = None
    product_type: str | None = None
    development_region: str | None = None
    compress_pngs: bool = True
    enable_on_demand_resources: bool = False
    coreui_profile: "str | None" = None
    optimize: str | None = None  # NextGen Optimization (smart/astc)'''

content = re.sub(r'@dataclass\nclass CompileOptions:.*?(?=\n\n)', new_options, content, flags=re.DOTALL)

with open("src_nextgen/actool_linux/compiler.py", "w") as f:
    f.write(content)
