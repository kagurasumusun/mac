"""Legacy CoreUI features and version-specific functionality.

This module provides support for CoreUI version-specific features,
target-specific functionality, and legacy compatibility modes.
"""

from typing import List, Tuple


# ============================================================================
# Version-Specific Features
# ============================================================================

class CoreUIVersionFeatures:
    """Features specific to different CoreUI versions."""

    # Version-specific feature flags and parameters
    VERSION_FEATURES = {
        # CoreUI 400-498 (MacOSX 10.5-10.6 era)
        400: {
            'max_image_size': 2048,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': False,
            'supports_svg': False,
            'max_color_stops': 8,
            'supported_compressions': ['raw', 'rle'],
            'key_format_version': 1,
            'max_facet_name_length': 64,
        },
        450: {
            'max_image_size': 2048,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': False,
            'supports_svg': False,
            'max_color_stops': 12,
            'supported_compressions': ['raw', 'rle', 'zlib'],
            'key_format_version': 1,
            'max_facet_name_length': 64,
        },
        498: {
            'max_image_size': 4096,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': False,
            'max_color_stops': 16,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse'],
            'key_format_version': 2,
            'max_facet_name_length': 128,
        },

        # CoreUI 580-680 (MacOSX 10.8-10.9 era)
        580: {
            'max_image_size': 4096,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': False,
            'max_color_stops': 20,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse'],
            'key_format_version': 2,
            'max_facet_name_length': 128,
            'supports_extended_metadata': True,
        },
        680: {
            'max_image_size': 8192,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': False,
            'max_color_stops': 24,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck'],
            'key_format_version': 3,
            'max_facet_name_length': 256,
            'supports_extended_metadata': True,
        },

        # CoreUI 700-850 (MacOSX 10.10-10.11 era)
        700: {
            'max_image_size': 8192,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': True,
            'max_color_stops': 32,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck'],
            'key_format_version': 3,
            'max_facet_name_length': 256,
            'supports_extended_metadata': True,
            'supports_multiple_databases': True,
        },
        800: {
            'max_image_size': 16384,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': True,
            'max_color_stops': 48,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck'],
            'key_format_version': 4,
            'max_facet_name_length': 512,
            'supports_extended_metadata': True,
            'supports_multiple_databases': True,
        },
        850: {
            'max_image_size': 16384,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': True,
            'max_color_stops': 64,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck'],
            'key_format_version': 4,
            'max_facet_name_length': 512,
            'supports_extended_metadata': True,
            'supports_multiple_databases': True,
            'supports_zero_code': True,
        },

        # CoreUI 918+ (MacOSX 10.12+ era)
        918: {
            'max_image_size': 32768,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': True,
            'max_color_stops': 128,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck', 'heif'],
            'key_format_version': 5,
            'max_facet_name_length': 1024,
            'supports_extended_metadata': True,
            'supports_multiple_databases': True,
            'supports_zero_code': True,
            'supports_texture_references': True,
        },
        975: {
            'max_image_size': 65536,
            'supports_alpha': True,
            'supports_grayscale': True,
            'supports_pdf': True,
            'supports_svg': True,
            'max_color_stops': 256,
            'supported_compressions': ['raw', 'rle', 'zlib', 'lzfse', 'cbck', 'heif', 'avif'],
            'key_format_version': 6,
            'max_facet_name_length': 2048,
            'supports_extended_metadata': True,
            'supports_multiple_databases': True,
            'supports_zero_code': True,
            'supports_texture_references': True,
            'supports_named_gradients': True,
            'supports_icon_stacks': True,
        },
    }

    @classmethod
    def get_features(cls, version: int) -> dict:
        """Get features for a specific CoreUI version."""
        # Find the highest version <= requested version
        available_versions = sorted(cls.VERSION_FEATURES.keys())
        target_version = max(v for v in available_versions if v <= version)
        return cls.VERSION_FEATURES[target_version]

    @classmethod
    def is_feature_supported(cls, version: int, feature: str) -> bool:
        """Check if a feature is supported in a specific version."""
        features = cls.get_features(version)
        return features.get(feature, False)

    @classmethod
    def get_max_image_size(cls, version: int) -> int:
        """Get maximum supported image size for a version."""
        features = cls.get_features(version)
        return features.get('max_image_size', 2048)

    @classmethod
    def get_supported_compressions(cls, version: int) -> List[str]:
        """Get supported compression methods for a version."""
        features = cls.get_features(version)
        return features.get('supported_compressions', ['raw'])


# ============================================================================
# Target-Specific Features
# ============================================================================

class TargetSpecificFeatures:
    """Features specific to different target platforms."""

    # Platform-specific parameters
    PLATFORM_FEATURES = {
        'macosx': {
            'default_scale': 2,
            'supported_scales': [1, 2, 3],
            'supported_idioms': ['mac', 'ipad', 'universal'],
            'supports_retina': True,
            'default_color_space': 'sRGB',
            'supported_color_spaces': ['sRGB', 'Display P3', 'Adobe RGB'],
            'max_atlas_size': 8192,
        },
        'iphoneos': {
            'default_scale': 3,
            'supported_scales': [1, 2, 3],
            'supported_idioms': ['iphone', 'ipad', 'universal'],
            'supports_retina': True,
            'default_color_space': 'sRGB',
            'supported_color_spaces': ['sRGB', 'Display P3'],
            'max_atlas_size': 4096,
        },
        'appletvos': {
            'default_scale': 2,
            'supported_scales': [1, 2],
            'supported_idioms': ['tv', 'universal'],
            'supports_retina': True,
            'default_color_space': 'sRGB',
            'supported_color_spaces': ['sRGB', 'Display P3'],
            'max_atlas_size': 8192,
        },
        'watchos': {
            'default_scale': 2,
            'supported_scales': [2],
            'supported_idioms': ['watch', 'universal'],
            'supports_retina': True,
            'default_color_space': 'sRGB',
            'supported_color_spaces': ['sRGB'],
            'max_atlas_size': 2048,
        },
        'xros': {
            'default_scale': 2,
            'supported_scales': [1, 2],
            'supported_idioms': ['vision', 'universal'],
            'supports_retina': True,
            'default_color_space': 'Display P3',
            'supported_color_spaces': ['sRGB', 'Display P3'],
            'max_atlas_size': 8192,
        },
    }

    @classmethod
    def get_features(cls, platform: str) -> dict:
        """Get features for a specific platform."""
        return cls.PLATFORM_FEATURES.get(platform, cls.PLATFORM_FEATURES['macosx'])

    @classmethod
    def get_supported_scales(cls, platform: str) -> List[int]:
        """Get supported scales for a platform."""
        features = cls.get_features(platform)
        return features.get('supported_scales', [1, 2])

    @classmethod
    def get_max_atlas_size(cls, platform: str) -> int:
        """Get maximum atlas size for a platform."""
        features = cls.get_features(platform)
        return features.get('max_atlas_size', 4096)


# ============================================================================
# Legacy Compatibility Modes
# ============================================================================

class LegacyCompatibilityMode:
    """Compatibility mode for legacy CoreUI versions."""

    def __init__(self, target_version: int, target_platform: str = 'macosx'):
        self.target_version = target_version
        self.target_platform = target_platform
        self.version_features = CoreUIVersionFeatures.get_features(target_version)
        self.platform_features = TargetSpecificFeatures.get_features(target_platform)

    def validate_image_size(self, width: int, height: int) -> Tuple[bool, str]:
        """Validate that image size is compatible with target version."""
        max_size = self.version_features.get('max_image_size', 2048)
        if width > max_size or height > max_size:
            return False, f"Image size {width}x{height} exceeds maximum {max_size}x{max_size} for CoreUI {self.target_version}"
        return True, ""

    def validate_compression(self, compression: str) -> Tuple[bool, str]:
        """Validate that compression method is compatible with target version."""
        supported = self.version_features.get('supported_compressions', ['raw'])
        if compression not in supported:
            return False, f"Compression '{compression}' not supported in CoreUI {self.target_version}. Supported: {supported}"
        return True, ""

    def validate_facet_name(self, name: str) -> Tuple[bool, str]:
        """Validate that facet name is compatible with target version."""
        max_length = self.version_features.get('max_facet_name_length', 64)
        if len(name) > max_length:
            return False, f"Facet name length {len(name)} exceeds maximum {max_length} for CoreUI {self.target_version}"
        return True, ""

    def validate_scale(self, scale: int) -> Tuple[bool, str]:
        """Validate that scale is compatible with target platform."""
        supported_scales = self.platform_features.get('supported_scales', [1, 2])
        if scale not in supported_scales:
            return False, f"Scale {scale} not supported on {self.target_platform}. Supported: {supported_scales}"
        return True, ""

    def validate_all(self, width: int, height: int, compression: str,
                     facet_name: str, scale: int) -> Tuple[bool, List[str]]:
        """Validate all parameters against target version and platform."""
        errors = []

        valid, msg = self.validate_image_size(width, height)
        if not valid:
            errors.append(msg)

        valid, msg = self.validate_compression(compression)
        if not valid:
            errors.append(msg)

        valid, msg = self.validate_facet_name(facet_name)
        if not valid:
            errors.append(msg)

        valid, msg = self.validate_scale(scale)
        if not valid:
            errors.append(msg)

        return len(errors) == 0, errors

    def get_recommended_compression(self) -> str:
        """Get recommended compression for target version."""
        supported = self.version_features.get('supported_compressions', ['raw'])
        # Prefer lzfse if available, then cbck, then zlib, then raw
        for pref in ['lzfse', 'cbck', 'zlib', 'raw']:
            if pref in supported:
                return pref
        return supported[0] if supported else 'raw'

    def get_recommended_atlas_size(self) -> int:
        """Get recommended atlas size for target platform."""
        max_size = self.platform_features.get('max_atlas_size', 4096)
        # Use 75% of max size for better packing efficiency
        return int(max_size * 0.75)


# ============================================================================
# Utility Functions
# ============================================================================

def get_version_specific_key_format(version: int) -> List[int]:
    """Get the key format attributes for a specific CoreUI version."""
    # Key format evolved over time
    if version < 500:
        return [0, 1, 2, 3, 4, 5, 6, 7]  # Basic attributes
    elif version < 700:
        return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # Added scale, idiom
    elif version < 900:
        return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Added appearance, localization
    else:
        return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]  # Added memory class, graphics class


def get_version_specific_header_format(version: int) -> dict:
    """Get header format parameters for a specific CoreUI version."""
    return {
        'coreui_version': version,
        'storage_version': 17 if version >= 918 else 16 if version >= 700 else 15,
        'schema_version': 2 if version >= 700 else 1,
        'key_semantics': 1,
    }


def create_legacy_compatible_car(version: int, platform: str = 'macosx') -> LegacyCompatibilityMode:
    """Create a legacy compatibility mode for CAR generation."""
    return LegacyCompatibilityMode(version, platform)
