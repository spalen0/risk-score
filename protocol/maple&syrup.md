# Maple Finance & Syrup

## [Impariment](https://maplefinance.gitbook.io/maple/maple-for-lenders/defaults-and-impairments)

When a loan is impaired, its value is temporarily reduced. This allows lenders who want to withdraw to access their capital with a penalty, while not fully defaulting the loan until the grace period has expired. If the Borrower is able to make the payment or repay, it will be changed to unimpaired, and the value of the pool will be restored based on the repayment.

If a new lender decided to deposit into the pool during an impairment, their lending balance will be affected by the impairment. If an impairment is able to be repaid in full, these depositors will be made whole, but will not have any claim to any forfeited recoveries by those who withdrew when the impairment was active. -> Meaning that you should not deposit into the pool during an impairment.

## [Margin Calls and Liquidations](https://maplefinance.gitbook.io/maple/maple-for-lenders/defaults-and-impairments-1)

"At any point, if collateralization reaches the Liquidation level, even if a margin call is in process, Maple has full rights to liquidate collateral to protect lender principal". Data can be fetched from Maple API.

## [Liqudations on Syrup](https://syrup.gitbook.io/syrup/troubleshooting-and-support/faq#at-what-rate-are-liquidation-levels-set-and-how-are-they-managed)

"Both Maple and Syrup loans are verifiable onchain with transparent margin call and liquidation levels for each individual loan".

## Collateral Assets on Syrup

### BTC

```json
{
  "asset": "BTC",
  "assetAmount": "6050000000",
  "liquidationLevel": 1111111,
  "liquidationThreshold": 50000,
  "marginCallLevel": 1176471,
  "marginCallThreshold": 20000,
  "assetValueUsd": "9662784000000",
  "name": "Syrup USDT",
  "id": "0x9b55aee465d48285e0de777975020a531b1dedd5"
}
```

LTV = 1 / (1176471 / 1000000) = 85%
Liquidation Level = 1 / (1111111 / 1000000) = 90%

Compared to [aave](https://app.aave.com/reserve-overview/?underlyingAsset=0x2260fac5e5542a773aa44fbcfedf7c193bc2c599&marketName=proto_mainnet_v3)
Max LTV = 73%
LLTV = 78%

Compared to [compound](https://app.compound.finance/markets/usdt-mainnet)
Max LTV = 80%
LLTV = 85%

Compared to [morpho wbtc/usdt market](https://app.morpho.org/ethereum/market/0xa921ef34e2fc7a27ccc50ae7e4b154e16c9799d3387076c421423ef52ac4df99/wbtc-usdt)
LLTV = 86%

### LBTC

```json
{
  "asset": "LBTC",
  "assetAmount": "9508000000",
  "liquidationLevel": 1176471,
  "liquidationThreshold": 50000,
  "marginCallLevel": 1333333,
  "marginCallThreshold": 50000,
  "name": "Syrup USDC",
  "id": "0x20d4cce9e045c9948ff7b28a62394c4a4ab14303"
}
```

LTV = 1 / (1333333 / 1000000) = 75%
Liquidation Level = 1 / (1176471 / 1000000) = 85%

Comapred to [aave](https://app.aave.com/reserve-overview/?underlyingAsset=0x8236a87084f8b84306f72007f36f2618a5634494&marketName=proto_mainnet_v3)
Max LTV = 70%
LLTV = 75%

Compared to [morpho lbtc/usdc market](https://app.morpho.org/ethereum/market/0xbf02d6c6852fa0b8247d5514d0c91e6c1fbde9a168ac3fd2033028b5ee5ce6d0/lbtc-usdc)
LLTV = 86%

### ETH

```json
{
  "asset": "ETH",
  "assetAmount": "5958990000000000000000",
  "liquidationLevel": 1176471,
  "liquidationThreshold": 40000,
  "marginCallLevel": 1428571,
  "marginCallThreshold": 40000,
  "assetValueUsd": "265857000000",
  "name": "Syrup USDC",
  "id": "0x9f0492ff1074aca7aa0b9c66215e24c276f912a8"
}
```

LTV = 1 / (1428571 / 1000000) = 70%
Liquidation Level = 1 / (1176471 / 1000000) = 85%

Compared to [aave](https://app.aave.com/reserve-overview/?underlyingAsset=0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2&marketName=proto_mainnet_v3)
Max LTV = 80.5%
LLTV = 83%

Compared to [compound](https://app.compound.finance/markets/usdc-mainnet)
Max LTV = 83%
LLTV = 90%

Compared to [morpho wsteth/usdc market](https://app.morpho.org/ethereum/market/0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc/wsteth-usdc)
LLTV = 86%

### tETH

```json
{
  "asset": "tETH",
  "assetAmount": "2506000000000000000000",
  "liquidationLevel": 1250000,
  "liquidationThreshold": 50000,
  "marginCallLevel": 1428571,
  "marginCallThreshold": 50000,
  "assetValueUsd": "317697290541",
  "name": "Syrup USDC",
  "id": "0x5b53d596cbf4a0e5d6438031ea501d260b0d1eaf"
}
```

LTV = 1 / (1428571 / 1000000) = 70%
Liquidation Level = 1 / (1250000 / 1000000) = 80%

Asset is not listed on aave, compound or morpho.

### SOL

```json
{
  "asset": "SOL",
  "assetAmount": "140000000000000000000000",
  "liquidationLevel": 1176471,
  "liquidationThreshold": 50000,
  "marginCallLevel": 1666667,
  "marginCallThreshold": 50000,
  "assetValueUsd": "18925500000",
  "name": "Syrup USDC",
  "principalOwed": "13000000000000",
  "id": "0xa69adda903fec32932ebbd753978773cb7c33aa0"
}
```

LTV = 1 / (1666667 / 1000000) = 60%
Liquidation Level = 1 / (1176471 / 1000000) = 85%

Asset is not listed on aave, compound or morpho.

### [Allocations](https://syrup.fi/details)

Data on 10th Feb 2025.

| Asset    | Allocation % | Amount      | Value (USD) |
|----------|-------------|-------------|-------------|
| SOL      | 31%         | 196,000     | $40M        |
| tETH     | 22%         | 9,262       | $29M        |
| ETH      | 16%         | 8,130       | $21M        |
| BTC      | 11%         | 156         | $15M        |
| PT_sUSDe | 10%         | 12,700,000  | $12.5M      |
| LBTC     | 6.9%        | 95          | $9M         |
| sUSDS    | 2%          | 2,600,000   | $2.6M       |

More than [15%](https://etherscan.io/token/0xD11c452fc99cF405034ee446803b6F6c1F6d5ED8#balances) of all tETH is used as collateral in Syrup(2 addresses), making it the top holder of tETH.

Swapping more than 1000 tETH for wstETH and tETH for weETH will cause more than 2% slippage. tETH allows immediate redemptions of tETH up to a 292.392 tETH limit at any given time for 2% fee. In the case of bigger tETH liquidation, the liquidator would have to accept tETH with 7 days to unwind the position.
