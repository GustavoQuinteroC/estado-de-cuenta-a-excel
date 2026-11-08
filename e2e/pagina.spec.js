import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (e) => { throw e; });
  page.on('console', (m) => { if (m.type() === 'error') throw new Error(m.text()); });
});

test('convierte el ejemplo, cuadra y descarga el Excel', async ({ page }) => {
  // El PDF no debe viajar a ningún lado: se registra todo POST que salga de la página.
  const envios = [];
  page.on('request', (r) => { if (r.method() !== 'GET') envios.push(r.url()); });

  await page.goto('./');
  await page.getByRole('button', { name: 'Probar con un ejemplo' }).click();
  await expect(page.locator('#estado')).toHaveText('12 movimientos listos para descargar.', { timeout: 100_000 });

  await expect(page.locator('#cuadre')).toHaveAttribute('data-cuadra', 'true');
  await expect(page.locator('#filas tr')).toHaveCount(12);
  await expect(page.locator('#filas tr').nth(2)).toContainText('SPEI RECIBIDO DE ABARROTES DON TACHO REF 7788123');
  await expect(page.locator('#periodo')).toContainText('2026');

  const descarga = page.waitForEvent('download');
  await page.locator('#descargar-excel').click();
  const archivo = await descarga;
  expect(archivo.suggestedFilename()).toBe('ejemplo-banco-ficticio.xlsx');
  const bytes = readFileSync(await archivo.path());
  expect(bytes.subarray(0, 2).toString()).toBe('PK');
  expect(envios).toEqual([]);
});

test('pide la contraseña de un PDF protegido', async ({ page }) => {
  await page.goto('./');
  await page.locator('#archivo').setInputFiles({ name: 'protegido.pdf', mimeType: 'application/pdf', buffer: readFileSync('e2e/protegido.pdf') });
  await expect(page.getByLabel('Contraseña del PDF')).toBeVisible({ timeout: 100_000 });
  await page.getByLabel('Contraseña del PDF').fill('mal');
  await page.getByRole('button', { name: 'Abrir' }).click();
  await expect(page.locator('#estado')).toContainText('La contraseña no abre el PDF');
  await page.getByLabel('Contraseña del PDF').fill('XAXX010101000');
  await page.getByRole('button', { name: 'Abrir' }).click();
  await expect(page.locator('#estado')).toHaveText('3 movimientos listos para descargar.');
});
