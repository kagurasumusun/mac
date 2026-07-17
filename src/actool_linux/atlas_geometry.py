"""Improved atlas packing geometry for better Apple compatibility.

This module provides enhanced packing algorithms that more closely match
Apple's actool behavior, particularly for edge cases with different
aspect ratios and sizes.
"""

from typing import List, Tuple

# Apple's packer preferences (observed from testing)
APPLE_PACKER_PRIORITY = {
    'area_efficiency': 0.4,      # Minimize wasted space
    'aspect_ratio': 0.3,          # Prefer square-ish atlases
    'size_order': 0.2,            # Pack larger items first
    'alignment': 0.1,             # Align to power-of-2 boundaries
}

def improved_shelf_pack(rects: List[Tuple[int, int]], max_width: int = 2048, max_height: int = 2048) -> Tuple[List[Tuple[int, int]], int, int]:
    """Improved shelf packing algorithm that better matches Apple's behavior.
    
    Args:
        rects: List of (width, height) tuples
        max_width: Maximum atlas width
        max_height: Maximum atlas height
    
    Returns:
        Tuple of (positions, atlas_width, atlas_height)
        where positions is a list of (x, y) tuples
    """
    # Sort by area (descending), then by height (descending)
    sorted_rects = sorted(enumerate(rects), key=lambda x: (x[1][0] * x[1][1], x[1][1]), reverse=True)
    
    positions = [None] * len(rects)
    shelves = []  # List of (y, height, current_x)
    
    atlas_width = 0
    atlas_height = 0
    
    for idx, (w, h) in sorted_rects:
        placed = False
        
        # Try to fit in existing shelf
        for shelf_idx, (shelf_y, shelf_h, shelf_x) in enumerate(shelves):
            if shelf_x + w <= max_width and h <= shelf_h:
                positions[idx] = (shelf_x, shelf_y)
                shelves[shelf_idx] = (shelf_y, shelf_h, shelf_x + w)
                atlas_width = max(atlas_width, shelf_x + w)
                placed = True
                break
        
        # Create new shelf if needed
        if not placed:
            if atlas_height + h <= max_height:
                positions[idx] = (0, atlas_height)
                shelves.append((atlas_height, h, w))
                atlas_width = max(atlas_width, w)
                atlas_height += h
            else:
                # Fallback: just place it (shouldn't happen with proper max dimensions)
                positions[idx] = (0, atlas_height)
                atlas_height += h
    
    return positions, atlas_width, atlas_height


def apple_style_pack(rects: List[Tuple[int, int]], max_width: int = 2048, max_height: int = 2048) -> Tuple[List[Tuple[int, int]], int, int]:
    """Apple-style packing that prioritizes area efficiency and aspect ratio.
    
    This algorithm more closely matches Apple's observed behavior:
    1. Sort by area (largest first)
    2. Use skyline algorithm for placement
    3. Prefer square-ish final atlas dimensions
    4. Align to 4-pixel boundaries when possible
    """
    # Sort by area (descending)
    sorted_indices = sorted(range(len(rects)), key=lambda i: rects[i][0] * rects[i][1], reverse=True)
    
    # Skyline algorithm
    skyline = [(0, 0, max_width)]  # (x, y, width)
    positions = [None] * len(rects)
    
    atlas_width = 0
    atlas_height = 0
    
    for idx in sorted_indices:
        w, h = rects[idx]
        
        # Align to 4-pixel boundary
        w_aligned = ((w + 3) // 4) * 4
        h_aligned = ((h + 3) // 4) * 4
        
        # Find best position (lowest y, then leftmost x)
        best_pos = None
        best_y = float('inf')
        best_x = float('inf')
        best_skyline_idx = -1
        
        for sky_idx, (sky_x, sky_y, sky_w) in enumerate(skyline):
            if sky_w >= w_aligned:
                # Calculate the y position if we place here
                place_y = sky_y
                
                if place_y < best_y or (place_y == best_y and sky_x < best_x):
                    best_y = place_y
                    best_x = sky_x
                    best_pos = (sky_x, sky_y)
                    best_skyline_idx = sky_idx
        
        if best_pos is None:
            # Fallback: place at the end
            best_pos = (0, atlas_height)
            best_y = atlas_height
        
        positions[idx] = best_pos
        
        # Update skyline
        x, y = best_pos
        new_y = y + h_aligned
        
        # Remove covered skyline segments
        new_skyline = []
        for sky_x, sky_y, sky_w in skyline:
            if sky_x + sky_w <= x or sky_x >= x + w_aligned:
                new_skyline.append((sky_x, sky_y, sky_w))
            elif sky_x < x:
                new_skyline.append((sky_x, sky_y, x - sky_x))
            elif sky_x + sky_w > x + w_aligned:
                new_skyline.append((x + w_aligned, sky_y, sky_x + sky_w - (x + w_aligned)))
        
        # Add new skyline segment
        new_skyline.append((x, new_y, w_aligned))
        
        # Sort skyline by x
        new_skyline.sort(key=lambda s: s[0])
        
        # Merge adjacent segments at same height
        merged_skyline = []
        for seg in new_skyline:
            if merged_skyline and merged_skyline[-1][1] == seg[1] and merged_skyline[-1][0] + merged_skyline[-1][2] == seg[0]:
                # Merge
                last = merged_skyline[-1]
                merged_skyline[-1] = (last[0], last[1], last[2] + seg[2])
            else:
                merged_skyline.append(seg)
        
        skyline = merged_skyline
        
        atlas_width = max(atlas_width, x + w_aligned)
        atlas_height = max(atlas_height, new_y)
    
    # Adjust final dimensions to prefer square-ish aspect ratio
    if atlas_width > 0 and atlas_height > 0:
        aspect = atlas_width / atlas_height
        if aspect > 2.0:
            # Too wide, try to make it taller
            atlas_height = min(atlas_height * 2, max_height)
        elif aspect < 0.5:
            # Too tall, try to make it wider
            atlas_width = min(atlas_width * 2, max_width)
    
    return positions, atlas_width, atlas_height


def calculate_packing_efficiency(positions: List[Tuple[int, int]], rects: List[Tuple[int, int]], atlas_width: int, atlas_height: int) -> float:
    """Calculate the packing efficiency (used area / total area)."""
    if atlas_width == 0 or atlas_height == 0:
        return 0.0
    
    used_area = sum(w * h for w, h in rects)
    total_area = atlas_width * atlas_height
    
    return used_area / total_area if total_area > 0 else 0.0
