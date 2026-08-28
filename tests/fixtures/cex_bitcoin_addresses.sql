{{ config(
        tags = ['static'],
        schema = 'cex_bitcoin',
        alias = 'addresses'
    )
}}

SELECT blockchain, address, cex_name, distinct_name, added_by, added_date
FROM (VALUES
    ('bitcoin', '1Cb1G5qFK91fShyaPPZWVFwYFBtqRG7h8D', 'Coinbase', 'Coinbase 1', 'hildobby', date '2023-04-06')
    , ('bitcoin', '1PJiGp2yDLvUgqeBsuZVCBADArNsk6XEiw', 'Binance', 'Binance 1', 'hildobby', date '2024-04-20')
    -- comment only
    ) AS x (blockchain, address, cex_name, distinct_name, added_by, added_date)
