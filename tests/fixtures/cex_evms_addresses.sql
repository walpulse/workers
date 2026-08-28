{{ config(
        tags = ['static'],
        schema = 'cex_evms',
        alias = 'addresses'
    )
}}

SELECT address, cex_name, distinct_name, added_by, added_date
FROM (VALUES
    -- Binance
    (0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be, 'Binance', 'Binance 1', 'hildobby', date '2022-08-28')
    , (0xD551234AE421e3BCBA99A0Da6D736074f22192FF, 'Binance', 'Binance 2', 'hildobby', date '2022-08-28')
    , (0x564286362092d8e7936f0549571a803b203aaced, 'Coinbase', 'Coinbase 1', 'hildobby', date '2023-04-06')
    ) AS x (address, cex_name, distinct_name, added_by, added_date)
