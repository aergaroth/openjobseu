import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// Wczytujemy mockowe dane z pliku JSON
const mockFeed = JSON.parse(fs.readFileSync(path.join(__dirname, 'mock-feed.json'), 'utf-8'));

test.beforeEach(async ({ page }) => {
  // Mockujemy odpowiedź dla zapytania o feed.json
  await page.route('**/feed.json', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockFeed),
    });
  });

  // Przechodzimy do strony głównej
  await page.goto('/');
});

test.describe('Frontend Main Page', () => {
  test('should display page title and main header', async ({ page }) => {
    await expect(page).toHaveTitle('OpenJobsEU — EU Remote Job Board');
    await expect(page.getByRole('heading', { name: 'Job feed' })).toBeVisible();
  });

  test('should load and display jobs from the feed', async ({ page }) => {
    // Elementy mają klasę .job-card wg struktury generowanej przez feed.js
    const jobCards = page.locator('.job-card');
    await expect(jobCards).toHaveCount(2);

    // Weryfikujemy treść pierwszej oferty
    const firstJob = jobCards.first();
    await expect(firstJob.locator('.job-title')).toHaveText('Senior Frontend Developer');
    await expect(firstJob.locator('.job-company')).toHaveText('TestCorp');
    // Regex jest użyty by zignorować ew. warianty spacji i separatorów tysięcy wynikające z ustawień regionalnych
    await expect(firstJob.locator('.job-salary')).toHaveText(/80[,.\s]*000 – 100[,.\s]*000 EUR/);

    // Weryfikujemy treść drugiej oferty (bez pensji)
    const secondJob = jobCards.nth(1);
    await expect(secondJob.locator('.job-title')).toHaveText('Junior Backend Developer');
    await expect(secondJob.locator('.job-company')).toHaveText('Innovate LLC');
    await expect(secondJob.locator('.job-salary')).toHaveCount(0);
  });

  test('should filter jobs by title search', async ({ page }) => {
    // Zgodnie z feed.js interakcja z polem wyszukiwarki działa z elementem #search
    await page.locator('#search').fill('Frontend');

    // Powinna zostać tylko jedna oferta
    const jobCards = page.locator('.job-card');
    await expect(jobCards).toHaveCount(1);
    await expect(jobCards.first().locator('.job-title')).toHaveText('Senior Frontend Developer');
  });

  test('should show "no results" message when search matches nothing', async ({ page }) => {
    await page.locator('#search').fill('NonExistentJob');

    await expect(page.locator('.job-card')).toHaveCount(0);

    // Dokładny tekst renderowany przez kod w feed.js
    await expect(page.getByText('No jobs match your filters.')).toBeVisible();
  });
});