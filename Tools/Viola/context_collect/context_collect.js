const puppeteer = require('puppeteer-core');
const { browser } = require('./config');
const { ContextCrawler } = require('./context_crawler');
const { DB } = require('./db');
const utility = require('./utility');

require('events').EventEmitter.defaultMaxListeners = 20;


(async () => {
    const db = await new DB();
    const crawler = await new ContextCrawler();
    crawler.db = db;
    crawler.collection = await db.mongoDatabase.collection('context_analyze');
    crawler.currentURL = '';

    const input_collection = await db.mongoDatabase.collection('input_collection');
    let from = 0;
    const batch_size = 100;
    while (1) {
        let inputs = await input_collection.find().skip(from).limit(batch_size).toArray();
        if (inputs.length === 0) {
            await utility.sleep(600000);
            continue;
        }
        for await (let input of inputs) {
            let url = input.url;
            let crawler_id = input.crawler_id;
            if (!url.startsWith('http')) {
                url = 'https://' + url;
            }

            let find_id = await crawler.collection.find({ "crawler_id": crawler_id }).toArray();
            let find_url = await crawler.collection.find({ "url": url }).toArray();
            if (find_id.length === 0 && find_url.length === 0) {
                try {
                    crawler.url = url;
                    crawler.crawler_id = crawler_id;
                    await crawler.newCrawlerTabs();
                } catch (error) {  // restart crawler
                    console.log(error);
                    await crawler.browser.close();
                    console.log('\nNew Browser...');
                    crawler.browser = await puppeteer.launch(browser);
                }
            }
        }
        from += inputs.length;
    }

    await crawler.close();
    process.exit(0);
})();
