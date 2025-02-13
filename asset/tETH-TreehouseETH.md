# tETH - TreehouseETH

tETH is a liquid staking token (LST) that converges the fragmented on-chain ETH interest rates market. Holders of tETH earn real yield in excess of Ethereum’s Proof-of-Stake (PoS) rewards through interest rate arbitrage while still being able to use tETH for DeFi activities. tETH is also foundational to supporting the implementation of Decentralized Offered Rates (DOR).

tETH is denominated in wstETH.

TVL on Treehouse is $277M, $200M on mainnet, on 5th Feb 2025 on [DefiLlama](https://defillama.com/protocol/treehouse-protocol).

## Centralization Risk

[Trail Of Bits](https://treehouse.finance/Trail_of_Bits_tETH_Sep_Audit_Report_vF.pdf) highlights centralization problems in Treehouse protocol:
> The system’s operations depend on certain privileged actors manually executing essential tasks (via off-chain executions). These tasks include operations related to profit and loss distribution, user withdrawals, updating state variables affecting user solvency and funds, and managing investments and divestments. Due to the extensible nature of the portfolio management system, privileged actors can perform arbitrary actions.

This centralization risk remains present in the protocol:
> TOB-TETH-2: a centralization risk and we acknowledge it as such - it's conceptually no different to another EOA with privileged access.

There is a Proxy Upgrade Risk with tETH contract [0xD11c452fc99cF405034ee446803b6F6c1F6d5ED8](https://etherscan.io/token/0xD11c452fc99cF405034ee446803b6F6c1F6d5ED8#code) uses ERC1967 Transparent Proxy pattern and admin can replace implementation without timelock. The admin is [multisig](https://etherscan.io/address/0x22261B4D6F629D8cF946C3524df86bF7222901F6#readProxyContract) 5/7.

## [Redemption Process](https://docs.treehouse.finance/protocol/teth/architecture/redemption-process)

Liquidity pool: tETH redemptions that are within the value of the Redemption Band will be facilitated through the tETH/wstETH Curve Liquidity Pool, allowing the immediate conversion of tETH to wstETH.

Curve Liquidity Pool:

- [wstETH/tETH Pool](https://curve.fi/dex/#/ethereum/pools/factory-stable-ng-270/deposit) - $10M TVL, 38/62 weight on 5th Feb 2025
- [weETH/tETH Pool](https://curve.fi/dex/#/ethereum/pools/factory-stable-ng-302/deposit) - $8 TVL, 40/60 weight on 5th Feb 2025

Normal redemption process: such redemptions are subject to a withdrawal period of approximately 7 days. This duration allows the protocol time to unwind the underlying LST assets back into native ETH to fulfill the redemption request.

Fast Redemption provides users who need instant access to their underlying assets. This allows immediate redemptions of tETH up to a certain limit at any given time for 2% fee.

## Links

- [tETH Contract](https://etherscan.io/token/0xD11c452fc99cF405034ee446803b6F6c1F6d5ED8#code)
- [Treehouse introduction](https://docs.treehouse.finance/protocol/teth/introduction)
- [Audits](https://docs.treehouse.finance/protocol/teth/security/audits)
- [Redemption Process](https://docs.treehouse.finance/protocol/teth/architecture/redemption-process)
