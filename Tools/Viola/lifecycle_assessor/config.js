const config = {
    browser: {
        executablePath: '',
        args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--ignore-certificate-errors',
            '--disable-features=UserAgentClientHint'
        ],
        ignoreDefaultArgs: ["--enable-automation"],
        headless: true
    },
    mongo: {
        db: '',
        uri: ''
    },
    mysql: {
        host: '',
        port: 0,
        user: '',
        password: '',
        database: ''
    },
    redis: {
        port: 0,
        host: '0',
        family: 0
    },
}


module.exports = config;
