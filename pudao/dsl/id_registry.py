# 简单内存"注册表"，只为 MVP 和示例策略服务

class IDRegistry:
    VALID_SEGMENTS = {
        "cd-se-101", "cd-se-102", "cd-se-103", "cd-se-104",
        "cd-ne-201", "cd-ne-202"
    }

    VALID_RAMPS = {
        "ramp-ne-201-in", "ramp-ne-202-in"
    }

    VALID_VMS = {
        "vms-ne-201-main", "vms-ne-150-bypass"
    }

    @staticmethod
    def is_valid_segment(seg_id: str) -> bool:
        return seg_id in IDRegistry.VALID_SEGMENTS

    @staticmethod
    def is_valid_ramp(ramp_id: str) -> bool:
        return ramp_id in IDRegistry.VALID_RAMPS

    @staticmethod
    def is_valid_vms(vms_id: str) -> bool:
        return vms_id in IDRegistry.VALID_VMS


id_registry = IDRegistry()
