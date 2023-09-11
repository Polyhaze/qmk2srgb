#!/usr/bin/env python3
# Copyright (c) 2023 Dylan Perks.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Converts a QMK keymap into a SignalRGB plugin.

import argparse
import glob
import jsoncomment
import os
import unicodedata

# format with:
# - keyboard name
# - vid
# - pid
# - num X
# - num Y
# - vkeys
# - vkeynames
# - vkeypositions

TEMPLATE = """export function Name() { return "$KNAME$ QMK Keyboard"; }
export function Version() { return "1.1.6"; }
export function VendorId() { return $VID$; }
export function ProductId() { return $PID$; }
export function Publisher() { return "Polyhaze (@Polyhaze) / Dylan Perks (@Perksey)"; }
export function Documentation(){ return "qmk/srgbmods-qmk-firmware"; }
export function Size() { return [$NX$, $NY$]; }
export function DefaultPosition(){return [10, 100]; }
export function DefaultScale(){return 8.0;}
/* global
shutdownMode:readonly
shutdownColor:readonly
LightingMode:readonly
forcedColor:readonly
*/
export function ControllableParameters()
{
    return [
        {"property":"shutdownMode", "group":"lighting", "label":"Shutdown Mode", "type":"combobox", "values":["SignalRGB", "Hardware"], "default":"SignalRGB"},
        {"property":"shutdownColor", "group":"lighting", "label":"Shutdown Color", "min":"0", "max":"360", "type":"color", "default":"#000000"},
        {"property":"LightingMode", "group":"lighting", "label":"Lighting Mode", "type":"combobox", "values":["Canvas", "Forced"], "default":"Canvas"},
        {"property":"forcedColor", "group":"lighting", "label":"Forced Color", "min":"0", "max":"360", "type":"color", "default":"#009bde"},
    ];
}

//Plugin Version: Built for Protocol V1.0.4

const vKeys = [
    $VK$
];

const vKeyNames = [
   $VKNAMES$
];

const vKeyPositions = [
    $VKPOS$
];

let LEDCount = 0;
let IsViaKeyboard = false;
const MainlineQMKFirmware = 1;
const VIAFirmware = 2;
const PluginProtocolVersion = "1.0.4";

export function LedNames() {
    return vKeyNames;
}

export function LedPositions() {
    return vKeyPositions;
}

export function vKeysArrayCount() {
    device.log('vKeys ' + vKeys.length);
    device.log('vKeyNames ' + vKeyNames.length);
    device.log('vKeyPositions ' + vKeyPositions.length);
}

export function Initialize() {
    requestFirmwareType();
    requestQMKVersion();
    requestSignalRGBProtocolVersion();
    requestUniqueIdentifier();
    requestTotalLeds();
    effectEnable();

}

export function Render() {
    sendColors();
}

export function Shutdown(SystemSuspending) {

    if(SystemSuspending) {
        sendColors("#000000"); // Go Dark on System Sleep/Shutdown
    } else {
        if (shutdownMode === "SignalRGB") {
            sendColors(shutdownColor);
        } else {
            effectDisable();
        }
    }

    vKeysArrayCount(); // For debugging array counts

}

function commandHandler() {
    const readCounts = [];

    do {
        const returnpacket = device.read([0x00], 32, 10);
        processCommands(returnpacket);

        readCounts.push(device.getLastReadSize());

        // Extra Read to throw away empty packets from Via
        // Via always sends a second packet with the same Command Id.
        if(IsViaKeyboard) {
            device.read([0x00], 32, 10);
        }
    }
    while(device.getLastReadSize() > 0);

}

function processCommands(data) {
    switch(data[1]) {
    case 0x21:
        returnQMKVersion(data);
        break;
    case 0x22:
        returnSignalRGBProtocolVersion(data);
        break;
    case 0x23:
        returnUniqueIdentifier(data);
        break;
    case 0x24:
        sendColors();
        break;
    case 0x27:
        returnTotalLeds(data);
        break;
    case 0x28:
        returnFirmwareType(data);
        break;
    }
}

function requestQMKVersion() //Check the version of QMK Firmware that the keyboard is running
{
    device.write([0x00, 0x21], 32);
    device.pause(30);
    commandHandler();
}

function returnQMKVersion(data) {
    const QMKVersionByte1 = data[2];
    const QMKVersionByte2 = data[3];
    const QMKVersionByte3 = data[4];
    device.log("QMK Version: " + QMKVersionByte1 + "." + QMKVersionByte2 + "." + QMKVersionByte3);
    device.log("QMK SRGB Plugin Version: "+ Version());
    device.pause(30);
}

function requestSignalRGBProtocolVersion() //Grab the version of the SignalRGB Protocol the keyboard is running
{
    device.write([0x00, 0x22], 32);
    device.pause(30);
    commandHandler();
}

function returnSignalRGBProtocolVersion(data) {
    const ProtocolVersionByte1 = data[2];
    const ProtocolVersionByte2 = data[3];
    const ProtocolVersionByte3 = data[4];

    const SignalRGBProtocolVersion = ProtocolVersionByte1 + "." + ProtocolVersionByte2 + "." + ProtocolVersionByte3;
    device.log(`SignalRGB Protocol Version: ${SignalRGBProtocolVersion}`);


    if(PluginProtocolVersion !== SignalRGBProtocolVersion) {
        device.notify("Unsupported Protocol Version: ", `This plugin is intended for SignalRGB Protocol version ${PluginProtocolVersion}. This device is version: ${SignalRGBProtocolVersion}`, 1, "Documentation");
    }

    device.pause(30);
}

function requestUniqueIdentifier() //Grab the unique identifier for this keyboard model
{
    if(device.write([0x00, 0x23], 32) === -1) {
        device.notify("Unsupported Firmware: ", `This device is not running SignalRGB-compatible firmware. Click the Open Troubleshooting Docs button to learn more.`, 1, "Documentation");
    }

    device.pause(30);
    commandHandler();
}


function returnUniqueIdentifier(data) {
    const UniqueIdentifierByte1 = data[2];
    const UniqueIdentifierByte2 = data[3];
    const UniqueIdentifierByte3 = data[4];

    if(!(UniqueIdentifierByte1 === 0 && UniqueIdentifierByte2 === 0 && UniqueIdentifierByte3 === 0)) {
        device.log("Unique Device Identifier: " + UniqueIdentifierByte1 + UniqueIdentifierByte2 + UniqueIdentifierByte3);
    }

    device.pause(30);
}

function requestTotalLeds() //Calculate total number of LEDs
{
    device.write([0x00, 0x27], 32);
    device.pause(30);
    commandHandler();
}

function returnTotalLeds(data) {
    LEDCount = data[2];
    device.log("Device Total LED Count: " + LEDCount);
    device.pause(30);
}

function requestFirmwareType() {
    device.write([0x00, 0x28], 32);
    device.pause(30);
    commandHandler();
}

function returnFirmwareType(data) {
    const FirmwareTypeByte = data[2];

    if(!(FirmwareTypeByte === MainlineQMKFirmware || FirmwareTypeByte === VIAFirmware)) {
        device.notify("Unsupported Firmware: ", "Click Show Console, and then click on troubleshooting for your keyboard to find out more.", 1, "Documentation");
    }

    if(FirmwareTypeByte === MainlineQMKFirmware) {
        IsViaKeyboard = false;
        device.log("Firmware Type: Mainline");
    }

    if(FirmwareTypeByte === VIAFirmware) {
        IsViaKeyboard = true;
        device.log("Firmware Type: VIA");
    }

    device.pause(30);
}

function effectEnable() //Enable the SignalRGB Effect Mode
{
    device.write([0x00, 0x25], 32);
    device.pause(30);
}

function effectDisable() //Revert to Hardware Mode
{
    device.write([0x00, 0x26], 32);
    device.pause(30);
}

function createSolidColorArray(color) {
    const rgbdata = new Array(vKeys.length * 3).fill(0);

    for(let iIdx = 0; iIdx < vKeys.length; iIdx++) {
        const iLedIdx = vKeys[iIdx] * 3;
        rgbdata[iLedIdx] = color[0];
        rgbdata[iLedIdx+1] = color[1];
        rgbdata[iLedIdx+2] = color[2];
    }

    return rgbdata;
}

function grabColors(overrideColor) {
    if(overrideColor) {
        return createSolidColorArray(hexToRgb(overrideColor));
    } else if (LightingMode === "Forced") {
        return createSolidColorArray(hexToRgb(forcedColor));
    }

    const rgbdata = new Array(vKeys.length * 3).fill(0);

    for(let iIdx = 0; iIdx < vKeys.length; iIdx++) {
        const iPxX = vKeyPositions[iIdx][0];
        const iPxY = vKeyPositions[iIdx][1];
        const color = device.color(iPxX, iPxY);

        const iLedIdx = vKeys[iIdx] * 3;
        rgbdata[iLedIdx] = color[0];
        rgbdata[iLedIdx+1] = color[1];
        rgbdata[iLedIdx+2] = color[2];
    }

    return rgbdata;
}

function sendColors(overrideColor) {
    const rgbdata = grabColors(overrideColor);

    const LedsPerPacket = 9;
    let BytesSent = 0;
    let BytesLeft = rgbdata.length;

    while(BytesLeft > 0) {
        const BytesToSend = Math.min(LedsPerPacket * 3, BytesLeft);
        StreamLightingData(Math.floor(BytesSent / 3), rgbdata.splice(0, BytesToSend));

        BytesLeft -= BytesToSend;
        BytesSent += BytesToSend;
    }
}

function StreamLightingData(StartLedIdx, RGBData) {
    const packet = [0x00, 0x24, StartLedIdx, Math.floor(RGBData.length / 3)].concat(RGBData);
    device.write(packet, 33);
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    const colors = [];
    colors[0] = parseInt(result[1], 16);
    colors[1] = parseInt(result[2], 16);
    colors[2] = parseInt(result[3], 16);

    return colors;
}

export function Validate(endpoint) {
    return endpoint.interface === 1;
}

export function Image() {
    return "";
}
"""

parser = argparse.ArgumentParser()
parser.add_argument("inputs", help="QMK info.json files (globs)", nargs="+")
parser.add_argument("--outdir", help="Output Directory for JS files", default=".")
parser.add_argument(
    "--matrix_sizing",
    help="Instead of being accurate to the original info.json (often generating very large sizes), the first "
    "coordinate for a given key matrix coordinate will be used for the entire column or row.",
    action="store_true",
    default=False,
)
args = parser.parse_args()

for i_glob in args.inputs:
    for i_file in glob.glob(i_glob, recursive=True):
        try:
            i_json = None
            with open(i_file, "r") as f:
                i_json = jsoncomment.JsonComment().loads(f.read())
            k_name = f"{i_json['manufacturer']} {i_json['keyboard_name']}"
            vid = i_json["usb"]["vid"]
            pid = i_json["usb"]["pid"]
            xs = list(
                set(
                    sorted(
                        x["x"] if not args.matrix_sizing or "matrix" not in x else x["matrix"][1]
                        for x in i_json["rgb_matrix"]["layout"]
                    )
                )
            )
            ys = list(
                set(
                    sorted(
                        x["y"] if not args.matrix_sizing or "matrix" not in x else x["matrix"][0]
                        for x in i_json["rgb_matrix"]["layout"]
                    )
                )
            )
            vkeys = ", ".join(str(x) for x in range(0, len(i_json["rgb_matrix"]["layout"])))
            vkeynames = []
            vkeypositions = []
            unnamed = 0
            matxs = {}
            matys = {}
            for led in i_json["rgb_matrix"]["layout"]:
                lbl = None
                ledx = xs.index(led["x"] if not args.matrix_sizing or "matrix" not in led else led["matrix"][1])
                ledy = ys.index(led["y"] if not args.matrix_sizing or "matrix" not in led else led["matrix"][0])
                if "matrix" in led and "layouts" in i_json:
                    ledx = matxs.setdefault(led["matrix"][0], ledx) if args.matrix_sizing else ledx
                    ledy = matys.setdefault(led["matrix"][1], ledy) if args.matrix_sizing else ledy
                    key = next(
                        (x for x in list(i_json["layouts"].values())[0]["layout"] if x["matrix"] == led["matrix"]), None
                    )
                    if key is not None and "label" in key:
                        lbl = key["label"]
                        if not lbl.isascii():
                            lbl = unicodedata.name(lbl)
                        if "\\" in lbl:
                            lbl = lbl.replace("\\", "\\\\")
                        if '"' in lbl:
                            lbl = lbl.replace('"', '\\"')
                if lbl is None:
                    unnamed += 1
                    lbl = f"Light {unnamed}"
                vkeynames.append(lbl)
                vkeypositions.append([ledx, ledy])
            vkeynames = ", ".join(f'"{x}"' for x in vkeynames)
            vkeypositions = ", ".join(str(x) for x in vkeypositions)
            o_file = os.path.join(
                args.outdir, f"{''.join(x for x in k_name if x.isalnum() or x == ' ').lower().replace(' ', '_')}.js"
            )
            with open(o_file, "w") as f:
                f.write(
                    TEMPLATE.replace("$KNAME$", k_name)
                    .replace("$VID$", vid)
                    .replace("$PID$", pid)
                    .replace("$NX$", str(len(xs)))
                    .replace("$NY$", str(len(ys)))
                    .replace("$VK$", vkeys)
                    .replace("$VKNAMES$", vkeynames)
                    .replace("$VKPOS$", vkeypositions)
                )
                print(f"Successfully created {o_file}")
        except Exception as e:
            print(f"Skipping {i_file} due to exception: {repr(e)}")
