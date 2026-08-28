#!/usr/bin/env python3
"""Generate Gazebo Harmonic model SDF from the migrated Collada assets.

Gazebo Harmonic's DART backend cannot use these meshes as collision geometry.
The source files are assemblies of transformed parts, so each part is converted
to a tight primitive box while the original mesh remains the visual geometry.
"""

from __future__ import annotations

import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "models" / "hangar"
NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}

STRUCTURE_ASSETS = (
    ("biela.dae", "concrete"),
    ("bokdvere.dae", "wood"),
    ("zarubna.dae", "steel"),
    ("strecha.dae", "brick"),
    ("bokstrecha.dae", "brick"),
    ("budkaoknadverebiela.dae", "white"),
    ("oknobok.dae", "white"),
    ("plechbok.dae", "concrete"),
    ("sklo.dae", "glass"),
    ("tienidlanaokno.dae", "steel"),
)

MATERIALS = {
    "concrete": """          <material>
            <ambient>0.42 0.44 0.46 1</ambient>
            <diffuse>0.72 0.73 0.72 1</diffuse>
            <specular>0.08 0.08 0.08 1</specular>
            <pbr><metal>
              <albedo_map>model://hangar/materials/textures/concrete_sum.jpg</albedo_map>
              <metalness>0.0</metalness><roughness>0.9</roughness>
            </metal></pbr>
          </material>""",
    "wood": """          <material>
            <ambient>0.28 0.20 0.08 1</ambient>
            <diffuse>0.55 0.38 0.14 1</diffuse>
            <specular>0.04 0.04 0.04 1</specular>
          </material>""",
    "steel": """          <material>
            <ambient>0.20 0.22 0.24 1</ambient>
            <diffuse>0.46 0.50 0.53 1</diffuse>
            <specular>0.55 0.55 0.55 1</specular>
            <pbr><metal><metalness>0.72</metalness><roughness>0.38</roughness></metal></pbr>
          </material>""",
    "brick": """          <material>
            <ambient>0.35 0.20 0.15 1</ambient>
            <diffuse>0.68 0.42 0.31 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
            <pbr><metal>
              <albedo_map>model://hangar/materials/textures/brick_texture.png</albedo_map>
              <metalness>0.0</metalness><roughness>0.92</roughness>
            </metal></pbr>
          </material>""",
    "white": """          <material>
            <ambient>0.66 0.68 0.69 1</ambient>
            <diffuse>0.86 0.87 0.86 1</diffuse>
            <specular>0.12 0.12 0.12 1</specular>
          </material>""",
    "glass": """          <material>
            <ambient>0.22 0.30 0.34 0.35</ambient>
            <diffuse>0.48 0.68 0.76 0.35</diffuse>
            <specular>0.75 0.75 0.75 1</specular>
          </material>
          <transparency>0.65</transparency>""",
    "rack": """          <material>
            <ambient>0.18 0.19 0.20 1</ambient>
            <diffuse>0.48 0.50 0.52 1</diffuse>
            <specular>0.62 0.62 0.62 1</specular>
            <pbr><metal>
              <albedo_map>model://hangar/materials/textures/steel_regal_texture.jpg</albedo_map>
              <metalness>0.68</metalness><roughness>0.42</roughness>
            </metal></pbr>
          </material>""",
}


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [
        [sum(a[row][k] * b[k][col] for k in range(4)) for col in range(4)]
        for row in range(4)
    ]


def transform(matrix: list[list[float]], point: list[float]) -> list[float]:
    vector = point + [1.0]
    return [sum(matrix[row][col] * vector[col] for col in range(4)) for row in range(3)]


def determinant3(matrix: list[list[float]]) -> float:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def matrix_to_rpy(matrix: list[list[float]]) -> tuple[float, float, float]:
    pitch = math.asin(max(-1.0, min(1.0, -matrix[2][0])))
    if abs(math.cos(pitch)) > 1e-8:
        roll = math.atan2(matrix[2][1], matrix[2][2])
        yaw = math.atan2(matrix[1][0], matrix[0][0])
    else:
        roll = math.atan2(-matrix[1][2], matrix[1][1])
        yaw = 0.0
    return roll, pitch, yaw


def collada_boxes(path: Path) -> list[tuple[str, list[float], list[float], tuple[float, float, float]]]:
    root = ET.parse(path).getroot()
    geometries: dict[str, tuple[list[float], list[float]]] = {}

    for geometry in root.findall(".//c:library_geometries/c:geometry", NS):
        mesh = geometry.find("c:mesh", NS)
        if mesh is None:
            continue
        vertices = mesh.find("c:vertices", NS)
        position = vertices.find('c:input[@semantic="POSITION"]', NS) if vertices is not None else None
        if position is None:
            continue
        source_id = position.get("source", "").removeprefix("#")
        source = mesh.find(f'c:source[@id="{source_id}"]', NS)
        if source is None:
            continue
        array = source.find("c:float_array", NS)
        accessor = source.find("c:technique_common/c:accessor", NS)
        if array is None or accessor is None or not array.text:
            continue
        values = list(map(float, array.text.split()))
        stride = int(accessor.get("stride", "3"))
        points = [values[index : index + 3] for index in range(0, len(values), stride)]
        geometries[geometry.get("id", "")] = (
            [min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)],
        )

    identity = [[1.0 if row == col else 0.0 for col in range(4)] for row in range(4)]
    boxes: list[tuple[str, list[float], list[float], tuple[float, float, float]]] = []

    def visit(node: ET.Element, parent: list[list[float]]) -> None:
        matrix_element = node.find("c:matrix", NS)
        if matrix_element is None or not matrix_element.text:
            local = identity
        else:
            values = list(map(float, matrix_element.text.split()))
            local = [values[index : index + 4] for index in range(0, 16, 4)]
        world = mat_mul(parent, local)
        instance = node.find("c:instance_geometry", NS)

        if instance is not None:
            bounds = geometries.get(instance.get("url", "").removeprefix("#"))
            if bounds is not None:
                low, high = bounds
                local_center = [(low[axis] + high[axis]) * 0.5 for axis in range(3)]
                local_size = [high[axis] - low[axis] for axis in range(3)]
                center = transform(world, local_center)
                columns = [[world[row][col] for row in range(3)] for col in range(3)]
                scales = [math.sqrt(sum(value * value for value in column)) for column in columns]
                rotation = [
                    [world[row][col] / scales[col] for col in range(3)]
                    for row in range(3)
                ]
                if determinant3(rotation) < 0:
                    for row in range(3):
                        rotation[row][0] *= -1
                size = [max(0.002, local_size[axis] * scales[axis]) for axis in range(3)]
                boxes.append((node.get("name", "part"), center, size, matrix_to_rpy(rotation)))

        for child in node.findall("c:node", NS):
            visit(child, world)

    scene = root.find(".//c:visual_scene", NS)
    if scene is None:
        raise RuntimeError(f"No visual scene in {path}")
    for node in scene.findall("c:node", NS):
        visit(node, identity)
    return boxes


def number(values: list[float] | tuple[float, ...]) -> str:
    return " ".join(f"{value:.7g}" for value in values)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "part"


def visual(name: str, filename: str, material: str) -> str:
    return f"""        <visual name="{safe_name(name)}_visual">
          <geometry><mesh><uri>model://hangar/{filename}</uri></mesh></geometry>
{MATERIALS[material]}
          <cast_shadows>true</cast_shadows>
        </visual>"""


def collisions(filename: str, prefix: str) -> list[str]:
    result = []
    for index, (name, center, size, rpy) in enumerate(collada_boxes(ASSET_DIR / filename)):
        result.append(f"""        <collision name="{prefix}_{index:03d}_{safe_name(name)}">
          <pose>{number(center)} {number(rpy)}</pose>
          <geometry><box><size>{number(size)}</size></box></geometry>
          <surface><friction><ode><mu>0.9</mu><mu2>0.9</mu2></ode></friction></surface>
        </collision>""")
    return result


def model_config(name: str, sdf_file: str, description: str) -> str:
    return f"""<?xml version="1.0"?>
<model>
  <name>{name}</name>
  <version>1.0</version>
  <sdf version="1.9">{sdf_file}</sdf>
  <description>{description}</description>
</model>
"""


def write_model(directory: str, model_name: str, description: str, body: list[str]) -> None:
    output = ROOT / "models" / directory
    output.mkdir(parents=True, exist_ok=True)
    (output / "model.config").write_text(
        model_config(model_name, "model.sdf", description), encoding="utf-8"
    )
    content = [
        '<?xml version="1.0"?>',
        '<sdf version="1.9">',
        f'  <model name="{model_name}">',
        "    <static>true</static>",
        '    <link name="body">',
        *body,
        "    </link>",
        "  </model>",
        "</sdf>",
        "",
    ]
    (output / "model.sdf").write_text("\n".join(content), encoding="utf-8")


def main() -> None:
    structure = []
    for filename, material in STRUCTURE_ASSETS:
        stem = Path(filename).stem
        structure.append(visual(stem, filename, material))
        structure.extend(collisions(filename, stem))
    write_model(
        "fei_lrs_hangar",
        "fei_lrs_hangar",
        "FEI LRS hangar structure with Harmonic-compatible primitive collisions.",
        structure,
    )

    racks = [visual("warehouse_racks", "regal.dae", "rack")]
    racks.extend(collisions("regal.dae", "rack"))
    write_model(
        "fei_lrs_racks",
        "fei_lrs_racks",
        "FEI LRS warehouse racks with per-member primitive collisions.",
        racks,
    )


if __name__ == "__main__":
    main()
