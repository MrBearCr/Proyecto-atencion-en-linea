import os

filepath = r"c:\Users\IT y Sistemas\post-warp\Proyecto-atencion-en-linea\pal\services\exports.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

tra_start = content.find("def export_tra_excel")
mbrp_start = content.find("def export_mbrp_excel")

# insert cache in export_tra_excel
ich_mode_tra_pos = content.find("ich_mode = sede_codigo in (None, '%', '00', 'ICH', 'ALL')", tra_start)
ich_mode_tra_end = content.find("\n", ich_mode_tra_pos)
insertion_tra = "\n        sedes_config_cache = config_manager.get_sedes_config() if config_manager else {}"
content = content[:ich_mode_tra_end] + insertion_tra + content[ich_mode_tra_end:]

mbrp_start = content.find("def export_mbrp_excel") # re-find after insertion

part1 = content[:tra_start]
part2 = content[tra_start:mbrp_start].replace("config_manager.get_sedes_config()", "sedes_config_cache")
part3 = content[mbrp_start:]
content = part1 + part2 + part3

# insert cache in export_mbrp_excel
mbrp_start = content.find("def export_mbrp_excel")
ich_mode_mbrp_pos = content.find("ich_mode = sede_codigo in (None, '%', '00', 'ICH', 'ALL')", mbrp_start)
ich_mode_mbrp_end = content.find("\n", ich_mode_mbrp_pos)
insertion_mbrp = "\n        sedes_config_cache = config_manager.get_sedes_config() if config_manager else {}"
content = content[:ich_mode_mbrp_end] + insertion_mbrp + content[ich_mode_mbrp_end:]

mbrp_start = content.find("def export_mbrp_excel")

part1 = content[:mbrp_start]
part2 = content[mbrp_start:].replace("config_manager.get_sedes_config()", "sedes_config_cache")
content = part1 + part2

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
