describe("App bootstrap", () => {
    it("renders root view", async () => {
      await device.launchApp();
      await expect(element(by.id("root"))).toBeVisible();
    });
  });
  