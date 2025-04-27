module.exports = {
    testRunner: "jest",
    runnerConfig: "e2e/config.json",
    apps: {
      "android.release": {
        type: "android.apk",
        binaryPath: "android/app/build/outputs/apk/release/app-release.apk",
      },
    },
    devices: {
      emulator: {
        type: "android.emulator",
        device: { avdName: "Pixel_4_API_33" },
      },
    },
    configurations: {
      "android.emu.release": { device: "emulator", app: "android.release" },
    },
  };
  