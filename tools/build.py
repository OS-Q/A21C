"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

https://github.com/GrumpyOldPizza/ArduinoCore-stm32l0
"""

from os.path import isdir, isfile, join

from SCons.Script import DefaultEnvironment

from platform import system

env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("A21C")
assert isdir(FRAMEWORK_DIR)

# board -> variant
VARIANT_REMAP = {
    "nucleo_l053r8": "STM32L053R8",
    "nucleo_l073rz": "STM32L073RZ"
}


def get_variant(board):
    variant = env.BoardConfig().get("build.variant", "")
    if board in VARIANT_REMAP:
        variant = VARIANT_REMAP[board]
    return variant


def get_mcu_family(mcu):
    family = mcu[0:9]
    # For some reasong L0x2 variant is used for L0x3 targets
    if mcu.startswith("stm32l053") or mcu.startswith("stm32l073"):
        family = family[:8] + '2'
    return family


def process_usb_configuration(cpp_defines):
    usb_type = "USB_TYPE_CDC"

    if "PIO_FRAMEWORK_ARDUINO_ENABLE_MASS_STORAGE" in cpp_defines:
        usb_type = "USB_TYPE_CDC_MSC"

    elif "PIO_FRAMEWORK_ARDUINO_ENABLE_HID" in cpp_defines:
        usb_type = "USB_TYPE_CDC_HID"

    elif "PIO_FRAMEWORK_ARDUINO_ENABLE_MASS_STORAGE_HID" in cpp_defines:
        usb_type = "USB_TYPE_CDC_MSC_HID"

    elif "PIO_FRAMEWORK_ARDUINO_NO_USB" in cpp_defines:
        usb_type = "USB_TYPE_NONE"

    env.Append(
        CPPDEFINES=[
            ("USB_TYPE", usb_type),
            ("USB_VID", board_config.get("build.hwids", [[0, 0]])[0][0]),
            ("USB_PID", board_config.get("build.hwids", [[0, 0]])[0][1]),
            ("USB_PRODUCT", '\\"%s\\"' % board_config.get(
                "build.usb_product", "$BOARD").replace('"', "")),
            ("USB_MANUFACTURER", '\\"%s\\"' % board_config.get(
                "vendor", "$BOARD").replace('"', ""))

        ]
    )


def process_fs_configuration(cpp_defines):
    sdcard = sflash = 0
    if "PIO_FRAMEWORK_ARDUINO_FS_SDCARD" in cpp_defines:
        sdcard = 1

    elif "PIO_FRAMEWORK_ARDUINO_FS_SFLASH" in cpp_defines:
        sflash = 1

    env.Append(
        CPPDEFINES=[
            ("DOSFS_SDCARD", sdcard),
            ("DOSFS_SFLASH", sflash)
        ]
    )


board_config = env.BoardConfig()
board_name = env.subst("$BOARD")
variant = get_variant(board_name)
variant_dir = join(FRAMEWORK_DIR, "variants", variant)
mcu = board_config.get("build.mcu", "")
cpu = board_config.get("build.cpu", "")
family = get_mcu_family(mcu)

cpp_defines = env.Flatten(env.get("CPPDEFINES", []))
process_usb_configuration(cpp_defines)
process_fs_configuration(cpp_defines)

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[
        "-std=gnu11"
    ],

    CXXFLAGS=[
        "-std=gnu++11",
        "-fno-threadsafe-statics",
        "-fno-rtti",
        "-fno-exceptions"
    ],

    CCFLAGS=[
        "-Os",
        "-w",
        "-mcpu=%s" % cpu,
        "-mthumb",
        "-ffunction-sections",
        "-fdata-sections",
        "-nostdlib",
        "-fsingle-precision-constant"
    ],

    CPPDEFINES=[
        ("ARDUINO", 10808),
        "ARDUINO_ARCH_STM32L0",
        "ARDUINO_%s" % board_name.upper(),
        ("BOARD_NAME", '\\"%s\\"' % board_name.upper()),
        ("_SYSTEM_CORE_CLOCK_", "$BOARD_F_CPU"),
        board_config.get("product_line", "%sxx" % family.upper())
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, "system", "CMSIS", "Include"),
        join(FRAMEWORK_DIR, "system", "CMSIS", "Device", "ST", "STM32L0xx",
            "Include"),
        join(FRAMEWORK_DIR, "system", "STM32L0xx", "Include"),
        join(FRAMEWORK_DIR, "cores", "arduino")
    ],

    LINKFLAGS=[
        "-Os",
        "-mthumb",
        "-mcpu=%s" % cpu,
        "--specs=nano.specs",
        "-fsingle-precision-constant",
        "-Wl,--gc-sections",
        "-Wl,--check-sections",
        "-Wl,--unresolved-symbols=report-all",
        "-Wl,--warn-common",
        "-Wl,--warn-section-align"
    ],

    LIBS=[
        "arm_cortex%sl_math" % cpu[7:9].upper(),
        "%sxx" % family, "c", "m"
    ],

    LIBPATH=[
        join(variant_dir, "linker_scripts"),
        join(FRAMEWORK_DIR, "system", "CMSIS", "Lib"),
        join(FRAMEWORK_DIR, "system", "STM32L0xx", "Lib")
    ],

    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR, "libraries")
    ]
)

if not board_config.get("build.ldscript", ""):
    env.Replace(LDSCRIPT_PATH="%s_FLASH.ld" % mcu[0:11].upper())

#
# Target: Build Core Library
#

libs = []

if "build.variant" in board_config:
    env.Append(
        CPPPATH=[variant_dir]
    )
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduinoVariant"),
        variant_dir
    ))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "FrameworkArduino"),
    join(FRAMEWORK_DIR, "cores", "arduino"))
)

env.Prepend(LIBS=libs)
