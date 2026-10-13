const fs = require('fs')
const path = require('path')
const puppeteer = require('puppeteer-core')

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
		browser = await puppeteer.launch({
			executablePath: '/home/dymes/.cache/puppeteer/chrome/linux-149.0.7827.22/chrome-linux64/chrome',
			headless: 'new',
			args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
		})

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
