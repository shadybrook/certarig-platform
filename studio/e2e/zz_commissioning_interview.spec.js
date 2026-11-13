import {expect, test} from '@playwright/test';

test('resume an incomplete interview, then onboard both fixture plants through reviewed proposals', async ({page}) => {
  await page.goto('/');
  await page.getByTestId('operator-key').fill('sim-operator-key-000001');
  await page.getByRole('button', {name:'Open Studio'}).click();
  await expect(page.locator('#health-pill')).toHaveAttribute('data-state','ok');
  await page.locator('#nav a[data-view="onboard"]').click();
  for (const [template, procedure] of [['pressure_flow','pressure_guardrail'],['thermal','thermal_soak']]) {
    await page.locator('#iv-create').click();
    await page.locator('#iv-propose').click();
    await expect(page.locator('#iv-blockers')).toContainText('Missing answer/source');
    await expect(page.locator('#iv-apply')).toBeDisabled();
    await page.reload();
    await expect(page.locator('#iv-blockers')).toContainText('Missing answer/source');
    await page.locator('#iv-equipment').fill(`${template} documented simulator fixture`);
    await page.locator('#iv-safe').selectOption('deenergized');
    await page.locator('#iv-procedures').fill(procedure);
    await page.locator('#iv-source').fill('Browser qualification fixture specification; not physical calibration');
    await page.locator('#iv-template').selectOption(template);
    await page.locator('#iv-template-load').click();
    await expect.poll(async () => JSON.parse(await page.locator('#iv-document').inputValue()).channels?.length || 0).toBeGreaterThan(0);
    const document = JSON.parse(await page.locator('#iv-document').inputValue());
    document.rig_id = `interview-${template.replaceAll('_','-')}`;
    await page.locator('#iv-document').fill(JSON.stringify(document,null,2));
    await Promise.all([
      page.waitForResponse(response => response.url().endsWith('/answers') && response.request().method() === 'POST' && response.ok()),
      page.locator('#iv-save').click(),
    ]);
    await page.locator('#iv-propose').click();
    await expect(page.locator('#iv-apply')).toBeEnabled();
    await expect(page.locator('#iv-preview')).toContainText('qualification');
    await page.locator('#iv-apply').click();
    await expect(page.locator('#commissioning-state')).toHaveAttribute('data-status','review_required');
    await expect(page.locator('#iv-resume')).toContainText('applied');
  }
});
