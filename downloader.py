import aiohttp

async def downloader(urls):
    api_url = "https://auto-download-all-in-one.p.rapidapi.com/v1/social/autolink"
    payload = {"url": urls}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": "0f95c9454bmshfbfff6f7be74315p12102djsnc98492887d39",
        "X-RapidAPI-Host": "auto-download-all-in-one.p.rapidapi.com"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=payload, headers=headers) as response:
            return await response.json()

