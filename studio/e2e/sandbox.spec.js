import { test, expect } from '@playwright/test';

async function login(page) {
  await page.goto('/');
  await page.getByTestId('operator-key').fill('sim-operator-key-000001');
  await page.getByRole('button',{name:'Open Studio'}).click();
  await expect(page.locator('#health-pill')).toHaveAttribute('data-state','ok');
  await page.locator('#nav a[data-view="sandbox"]').click();
}

test('sandbox accurately reports disabled runtime without a host fallback',async({page},testInfo)=>{
  await login(page);
  await expect(page.getByRole('heading',{name:'Runtime unavailable'})).toBeVisible();
  await expect(page.locator('#sb-status')).toContainText('Local sandbox broker is not configured');
  await expect(page.getByRole('button',{name:'Run bounded Python'})).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath('sandbox-blocked.png'),fullPage:true});
});

test('sandbox frontend fixture keeps blocked execution disabled and escapes artifact text',async({page})=>{
  // UI fixture only. This is not a backend or container qualification.
  const id='sbx_1111111111111111';
  const job='job_2222222222222222';
  const workspace={sandbox_id:id,status:'active',revision:0,snapshot:{evidence_kind:'UI fixture, not qualification',document:{rig_id:'fixture'},procedure:{id:'fixture'}},jobs:[{job_id:job,kind:'python',status:'completed',error:'<script>bad()</script>',artifacts:{'analysis.json':'hash'},qualification:false}],proposals:[]};
  await page.route('**/v1/sandboxes/preflight',r=>r.fulfill({json:{enabled:true,ready:false,blockers:['Fixture resource preflight blocked']}}));
  await page.route('**/v1/sandboxes',r=>r.fulfill({json:{workspaces:[workspace]}}));
  await page.route(`**/v1/sandboxes/${id}/jobs/${job}/artifacts/analysis.json`,r=>r.fulfill({contentType:'text/plain',body:'<img src=x onerror="bad()">'}));
  await login(page);
  await page.locator('#sb-select').selectOption(id);
  await expect(page.getByRole('button',{name:'Run bounded Python'})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Rehearse this exact revision'})).toBeDisabled();
  await expect(page.locator('#sb-details')).toContainText('Experiment output only; no qualification receipt.');
  await page.getByRole('button',{name:'analysis.json',exact:true}).click();
  await expect(page.locator('#sb-artifact pre')).toHaveText('<img src=x onerror="bad()">');
  await expect(page.locator('#sb-artifact img')).toHaveCount(0);
});
