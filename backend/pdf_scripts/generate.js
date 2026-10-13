const fs = require('fs')
const path = require('path')
const puppeteer = require('puppeteer')

async function main() {
	const inputPath = process.argv[2]

	if (!inputPath) {
		console.error('Usage: node generate.js <path-to-html>')
		process.exit(1)
	}

	const resolvedPath = path.resolve(inputPath)

	if (!fs.existsSync(resolvedPath)) {
		console.error(`HTML file not found: ${resolvedPath}`)
		process.exit(1)
	}

	const fileUrl = new URL(`file://${resolvedPath}`)

	let browser
	try {
		const launchOptions = {
			headless: 'new',
			args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
		}

		// Optional override for environments where Chromium is managed externally.
		if (process.env.CHROME_PATH) {
			launchOptions.executablePath = process.env.CHROME_PATH
		}

		browser = await puppeteer.launch(launchOptions)

		const page = await browser.newPage()
		await page.goto(fileUrl.href, { waitUntil: 'networkidle0' })

		const pdfBuffer = await page.pdf({
			format: 'A4',
			printBackground: true,
			preferCSSPageSize: true,
		})

		process.stdout.write(pdfBuffer)
	} catch (err) {
		console.error(err?.stack || String(err))
		process.exit(1)
	} finally {
		if (browser) {
			await browser.close()
		}
	}
}

main()
