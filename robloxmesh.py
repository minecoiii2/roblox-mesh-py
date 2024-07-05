'''
Python implementation of a RobloxMesh decoder for version 2+
'''

import bufferlua

def strip_from_tuple(str: str): # idk
    return str.replace("(", "").replace(")", "").replace(",", "")

class RobloxMesh():
    def __init__(self, content: bytes):
        buffer = bufferlua.Buffer(content)

        self.version = 4 # TODO VERSION DETECTING
        self.buffer = buffer

        buffer.skip(13)
        buffer.skip(2)

        if self.version >= 4:
            buffer.skip(2)

            self.verts_count = buffer.read_unit(32)
            self.faces_count = buffer.read_unit(32)

            self.lods_count = buffer.read_unit(16)

            self.bones_count = buffer.read_unit(16)
            self.bones_name_size = buffer.read_unit(32)

            self.subset_count = buffer.read_unit(16)

            buffer.skip(2)

            if self.version >= 5:
                self.facts_data_type = buffer.read_unit(32)
                buffer.skip(4)

            self.verts_size = 40
        else:
            self.verts_size = buffer.read_unit(8)
            buffer.skip(1)

            if self.version >= 3:
                buffer.skip(2)
                self.lods_count = buffer.read_unit(16)

            self.verts_count = buffer.read_unit(32)
            self.faces_count = buffer.read_unit(32)

        self.verts = []
        self.bones = []
        self.bone_map =[]
        self.faces = []
        self.lod_offsets = []
        self.envelopes = []

        # verts

        for i in range(self.verts_count):	
            vert = {
                'Weights': {},
                'Color': {
                    'Tint': (1, 1, 1),
                    'Alpha': 1,
                },

                'Position': buffer.read_vector3(),
                'Normal': buffer.read_vector3(),
                'UV': buffer.read_vector2()
            }

            xyzs = buffer.read_unit(32)

            if xyzs != 0:
                tx = xyzs % 256
                ty = xyzs >> 8 % 256
                tz = (xyzs >> 16) % 256
                ts = (xyzs >> 24) % 256

                vert["Tangent"] = { # probably doesnt work
                    'Sign': (ts - 127) / 127,

                    'Vector': (
                        (tx - 127) / 127,
                        (ty - 127) / 127,
                        (tz - 127) / 127
                    )
                }

            if self.verts_size > 36:
                vert["Color"] = {
                    'Tint': (buffer.read_unit(8) / 255, buffer.read_unit(8) / 255, buffer.read_unit(8) / 255),
                    'Alpha': buffer.read_unit(8) / 255,
                }

            self.verts.append(vert)

        # envelopes 

        if self.bones_count > 0:
            for i in range(self.verts_count): # not sure if it works
                self.envelopes.append({
                    'Bones': buffer.read_mul_units(4),
                    'Weights': buffer.read_mul_units(4),
                })
        
        # faces

        for i in range(self.faces_count):
            a, b, c = buffer.read_unit(32) + 1, buffer.read_unit(32) + 1, buffer.read_unit(32) + 1
            self.faces.append((a, b, c))

        # LOD offsets

        for i in range(self.lods_count):
            self.lod_offsets.append(buffer.read_unit(32))

        if self.lods_count < 2 or self.lod_offsets[1] == 0:
            self.lod_offsets = [0, self.faces_count]
            self.lods_count = 2

        # bones

        for i in range(self.bones_count):
            bone = {
                'name_index': buffer.read_int(32),
                'parent_id': buffer.read_unit(16),
                'lod_parent_id': buffer.read_unit(16),
                'culling': buffer.read_float(32),

                'm1': buffer.read_vector3(),
                'm2': buffer.read_vector3(),
                'm3': buffer.read_vector3(),
                'm0': buffer.read_vector3()	
            }

            self.bones.append(bone)
            

        # bone names

        bone_names = buffer.read_bytes(self.bones_name_size)

        for v in self.bones:
            startAt = v["name_index"]
            endAt = bone_names.find("\0", startAt)

            if endAt >= 0:
                name = bone_names[startAt, endAt - 1]
                self.bone_map[name] = v # TODO finish this whole section

        # bone subsets

        for i in range(self.subset_count):
            faces_begin = buffer.read_unit(32)
            faces_len = buffer.read_unit(32)

            verts_begin = buffer.read_unit(32)
            verts_end = verts_begin + buffer.read_unit(32)

            bones_num = buffer.read_unit(32)
            bone_subset = [0] * 26

            for v in range(verts_begin + 1, verts_end):
                vert = self.verts[v]
                envelope = self.envelopes[v]

                for i in range(4):
                    subset_index = envelope["Bones"][i]
                    bone_id = bone_subset[subset_index]

                    if bone_id != 0xFFFF:
                        bone = self.bones[bone_id]
                        weight = envelope["Weights"][i]

                        if weight > 0:
                            vert["Weights"][bone] = 0 # TODO FIX NAMES TO WRAP UP IN BONES

        # break up faces by LOD

        self.lods = []

        for L in range(self.lods_count - 1):
            lod_start = self.lod_offsets[L]
            lod_end = min(self.lod_offsets[L + 1], self.faces_count)

            lod = []

            for i in range(lod_start + 1, lod_end):
                face = self.faces[i]
                lod.append(face)

            self.lods.append(lod)

    def export(self, fp: str):
        '''
        Exports as .obj file
        '''
        fp = fp.replace(".obj", "")

        with open(fp + ".obj", "w") as file:
            file.write("# Made by MinecoIII2; Roblox: MinecoIII2, Discord: minecoiii\ng\n")

            for i in range(self.verts_count): #TODO only load used verts
                v = self.verts[i]
                pos, uv = v["Position"], v["UV"]

                file.write(strip_from_tuple(f"v {pos[0]} {pos[1]} {pos[2]}\nvt {uv[0]} {uv[1]}\n"))

            for i in range(len(self.lods[0])):
                v = self.lods[0][i]

                file.write(strip_from_tuple(f"f {v[0]}/{v[0]} {v[1]}/{v[1]} {v[2]}/{v[2]}\n"))
            
            file.write("s off")

def fromFp(fp: str):
    '''
    Opens RobloxMesh from filepath
    '''
    content = None
    with open(fp, "rb") as file:
        content = file.read()

    return RobloxMesh(content)
