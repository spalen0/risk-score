# VEDA Protocol Analysis

## Summary

VEDA Protocol implements a modular DeFi vault system where components interact through a complex role-based authority structure. The system consists of a BoringVault that holds assets and issues shares, a Teller for handling deposits and withdrawals, an Accountant managing exchange rates, a Manager executing actions using vault funds, and an AtomicQueue processing withdrawal requests. This architecture achieves flexibility through decoupling, with each component operating independently while communicating through well-defined interfaces.

The protocol's security is primarily governed by an AuthorityRoles contract that provides granular, function-level permission control across 10 distinct role groups. While this design enables precise access management, it introduces significant centralization risks as the 4/6 multisig controlling the Authority contract for [USDC Boring Vault](https://etherscan.io/address/0x08c6F91e2B681FaF5e17227F2a44C307b3C1364C). It can add access to exit function on vault contract and sweep all funds. User withdrawals can be blocked at any time by changing permissions. Exchange rates can be manipulated within allowed ranges, and multiple pausing mechanisms exist that could trap user funds indefinitely.

Despite these concerns, the system incorporates some positive features such as rate change limitations, multiple withdrawal paths, and multisig governance requirements. However, the lack of interdependencies between modules means permissioned accounts can execute critical functions without cross-component verification, creating potential security vulnerabilities if the controlling entities act maliciously or are compromised. Using timelock as owner of AuthorityRoles would improve security and trust in the protocol governance.

## Documentation & Resources

- [All off-chain algorithms](https://docs.veda.tech/#flexible-off-chain-algorithms)
- [Contracts repository](https://github.com/Se7en-Seas/boring-vault/)
- [Funds flow](https://docs.veda.tech/integrations/ui-integration)

## Protocol Analysis

VEDA protocol is a modular DeFi vault system where components interact through a complex role-based authority structure. The main components are:

### Teller

- [TellerWithMultiAssetSupport contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/TellerWithMultiAssetSupport.sol)
- Documentation typo: [Incorrect isPaused() call reference](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/TellerWithMultiAssetSupport.sol#L190)
- Can blacklist users for transferring vault shares but [cannot block withdrawals](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/TellerWithMultiAssetSupport.sol#L236)
- All deposit and withdraw functions are behind [`requiresAuth()`](https://github.com/transmissions11/solmate/blob/c892309933b25c03d32b1b0d674df7ae292ba925/src/auth/Auth.sol#L24) modifier which can block all interactions

### Accountant

- [AccountantWithRateProviders contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/AccountantWithRateProviders.sol)
- [Suspicious comment about updating rates](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/AccountantWithRateProviders.sol#L290)
- Exchange rate can be updated as long as it's within [allowedExchangeRateChange Upper/Lower range](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/AccountantWithRateProviders.sol#L468)
- Updating cannot be updated too fast, it's limited by `minimumUpdateDelayInSeconds` parameter.
- If rate is outside range: vault pauses, blocks claiming fee and getRateInQuoteSafe(), which [blocks all deposit/withdrawals](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/TellerWithMultiAssetSupport.sol#L455C55-L455C73)

### Manager

- [ManagerWithMerkleVerification contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/ManagerWithMerkleVerification.sol)
- ManagerWithMerkleVerification defines [root hash of manager actions](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/ManagerWithMerkleVerification.sol#L26)
- uManager wraps additional functionality to ManagerWithMerkleVerification
- SymbioticUManager uses completely different flow for verification

### BoringVault

- [BoringVault contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/BoringVault.sol)
- Contract that holds funds and issues ERC20 tokens as representation of shares
- Accepts different ERC20 tokens
- beforeTransfer hook can be set for minted ERC20 shares
- All function permissions managed using [`requiresAuth()`](https://github.com/transmissions11/solmate/blob/c892309933b25c03d32b1b0d674df7ae292ba925/src/auth/Auth.sol#L24)

### AtomicQueue

- [AtomicQueue contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/atomic-queue/AtomicQueue.sol)
- AtomicQueue is used for withdrawing funds from vault. User creates a request in `AtomicQueue` contract and AtomicSolvers fill it.
- AtomicQueue can be [paused](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/atomic-queue/AtomicQueue.sol#L478) by Authority contract to block all withdrawals.
- AtomicSolverV3 is allowed to call bulkWithdraw.
- AtomicSolverV3 has [`AtomicQueue`](https://github.com/Se7en-Seas/boring-vault/blob/main/src/atomic-queue/AtomicQueue.sol) as a parameter which contains implementation of withdrawals.
- There is also WithdrawQueue contract which can be used for withdrawing funds from vault. Withdrawals function request is controlled by the same [`requiresAuth()`](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/WithdrawQueue.sol#L366) modifier.

## User Flows

- Deposit flow example: User calls deposit on Teller → Teller calls BoringVault → Vault mints shares without validation
- Withdraw exit flow [example](https://dashboard.tenderly.co/yearn/sam/tx/0x74ea5a8c82149d36aa296406a93ddb874ae7aa8acf0eeddc8bbe0d1b1308d5de): User creates a request in AtomicQueue by calling [`updateAtomicRequest()`](https://etherscan.io/address/0x3b4acd8879fb60586ccd74bc2f831a4c5e7dbbf8#code#F1#L236) → AtomicSolverV3 fills the request → TellerWithMultiAssetSupport.bulkWithdraw() is called → BoringVault burns shares and sends assets → assets end up in the queue → Solver sends assets to user
- Withdraw p2p flow example: User creates a request in AtomicQueue → AtomicSolverV3 fills the request → Swaps shares for assets sends them to user

## Security Concerns

- Withdrawals can be blocked at any time by setting auth address for function signature
- No dependency between modules/contracts, meaning permissioned accounts can do almost anything
- All core function access can be changed by Authority contract
- Authority contract owner is 4/6 multisig
<<<<<<< HEAD
- Exchange rates are update without onchain verification
=======
>>>>>>> master
- Exchange rates can be manipulated within defined ranges, potentially favoring certain exits or causing accounting errors
- Exchage rate is updated by 2/4 multisig
- Exchange rate can be updated every [6 hours](https://etherscan.io/address/0xbe16605b22a7facef247363312121670dfe5afbe#readContract#F1) and only by 0.5% down without pausing Accountant contract. Pausing the contract will block any withdrawal because calcuclating rate in [Teller contract](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/TellerWithMultiAssetSupport.sol#L455C55-L455C73) will [revert](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/AccountantWithRateProviders.sol#L388).
- [ManageRoot](https://github.com/Se7en-Seas/boring-vault/blob/0e23e7fd3a9a7735bd3fea61dd33c1700e75c528/src/base/Roles/ManagerWithMerkleVerification.sol#L33) in ManagerWithMerkleVerification doesn't reveal what actions are allowed.

## Monitroing

Set up monitoring for following to mitigate centralization risks:

- `AuthorityRoles` owner and changes in this contract.
- `AccountantWithRateProviders.updateExchangeRate()` function and if it will trigger pausing of this contract.
- `AccountantWithRateProviders` for variables updates like delay and lower/upper bounds. This could be covered by monitoring `AuthorityRoles` owner.
- `ManagerWithMerkleVerification` for changes in merkle root. This could be covered by monitoring `AuthorityRoles` owner.

## Deployed Examples

- [USDC Boring Vault](https://etherscan.io/address/0x08c6F91e2B681FaF5e17227F2a44C307b3C1364C)
- [TellerWithMultiAssetSupport](https://etherscan.io/address/0x221Ea02d409074546265CCD1123050F4D498ef64#code)
- [Authority Contract Owner (4/6 multisig)](https://etherscan.io/address/0xCEA8039076E35a825854c5C2f85659430b06ec96#code)
- [Authority Roles Contract](https://etherscan.io/address/0xaBA6bA1E95E0926a6A6b917FE4E2f19ceaE4FF2e#code)
- [AccountantWithRateProviders](https://etherscan.io/address/0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7#code)
- [ManagerWithMerkleVerification](https://etherscan.io/address/0xcff411d5c54fe0583a984bee1ef43a4776854b9a#code)
- [AtomicQueue](https://etherscan.io/address/0x3b4acd8879fb60586ccd74bc2f831a4c5e7dbbf8#code)
- [Deposit Example (Tenderly)](https://dashboard.tenderly.co/tx/0xd48613d3315eed3113dd1c6c2a2cb73f2e416fecb09aa16001251ce26dd0e34a?trace=0.5.2.0)
- [Exit Example (Tenderly)](https://dashboard.tenderly.co/tx/0xbf5967757dc451eca933a0bc1410a01486a4dbd0a60225b76bdf8604060b23f8?trace=0.5.2.0)
- [Update Exchange Rate Example (Tenderly)](https://dashboard.tenderly.co/yearn/sam/tx/0x65dcb4f418bb6c52a34e1e7e70673bd4224dda57aba97f1323b41694f62b6ea1?trace=0.1.7.0.0). Update by Gnosis multisig 2/4.

Solver example:

- [AtomicSolverV3](https://etherscan.io/address/0x989468982b08AEfA46E37CD0086142A86fa466D7#code)
- [Atomic solver authority](https://etherscan.io/address/0x4df6b73328B639073db150C4584196c4d97053b7)
- Atomic solver owner and Auth owner for Atomic solver is [EOA Kraken](https://etherscan.io/address/0x989468982b08aefa46e37cd0086142a86fa466d7#readContract#F2)

## Authorization Groups

[Authority Roles Contract](https://etherscan.io/address/0xaBA6bA1E95E0926a6A6b917FE4E2f19ceaE4FF2e#code) has following groups of roles, each with different permissions. For contract implementation details see [solmate repository](https://github.com/transmissions11/solmate/blob/c892309933b25c03d32b1b0d674df7ae292ba925/src/auth/Auth.sol).

### Group 1

- Can do following: BoringVault.manage(): [added](https://etherscan.io/tx/0x045241c702f1d7c8285c0519922d826005a57e336afacdfa3f17cbfde5596c8e#eventlog)
- Merkle(0xcFF411d5C54FE0583A984beE1eF43a4776854B9A): [added](https://etherscan.io/tx/0x235bfd348c8186c6a9cb9cc8407ce0b49a21d428744d6f92d4613a4b5d4c84d7#eventlog)

### Group 2

- Can do following: BoringVault.enter(): [added](https://etherscan.io/tx/0x50986de941261dddfec8cd8e609c2fbd55e8b315ed1b77055b5f40682cab594c#eventlog)
- Teller(0x221Ea02d409074546265CCD1123050F4D498ef64): [added](https://etherscan.io/tx/0xf080db03258eb59bc93f43a23dd0b593ca3ae5da2337bb5a402824780356cccb#eventlog) → [removed](https://etherscan.io/tx/0x2e64714634f87b27f580e8b24c61a4d4e381aef28e4e7cfa68b5098be303e5cc#eventlog)

### Group 3

- Can do following: BoringVault.exit(): [added](https://etherscan.io/tx/0x7c382c7a8733dc68d449b938cea0d775093683a199f5aecd750ad4396418fdaa#eventlog)
- Teller(0x221Ea02d409074546265CCD1123050F4D498ef64): [added](https://etherscan.io/tx/0x0e08e292dc99ba0c0d9e89f3a0f0ae2db70966d41b13c99d9e2fb17db16839ff#eventlog)
- TellerWithMultiAssetSupport(0x221Ea02d409074546265CCD1123050F4D498ef64): [added](https://etherscan.io/tx/0xa19a7835401364c4ac59c9a1c7c939ba72fc8b13b55c207cd0eeba49c9173da8#eventlog)

### Group 4

- Can do following: ManagerWithMerkleVerification.manageVaultWithMerkleVerification(): [added](https://etherscan.io/tx/0x8ea3fda57a54ea5a5267156b96e17b12b209073e614b5adbe12e7b639681cb52#eventlog)
- Merkle(0xcFF411d5C54FE0583A984beE1eF43a4776854B9A): [added](https://etherscan.io/tx/0x8ea3fda57a54ea5a5267156b96e17b12b209073e614b5adbe12e7b639681cb52#eventlog)
- Merkle(0xcFF411d5C54FE0583A984beE1eF43a4776854B9A): [added](https://etherscan.io/tx/0x71880b64755465bc891a931f0d9653ab2e8c66fa523c06452dee6c41d6083e99#eventlog)
- ManagerWithMerkleVerification(0xcFF411d5C54FE0583A984beE1eF43a4776854B9A): [added](https://etherscan.io/tx/0x8a297de4d715b1e963d4dc3a18dea6649d70c3d2784ccb6db66cbc762d59de33#eventlog)

### Group 7

- Can do following: Merkle.manageVaultWithMerkleVerification(): [added](https://etherscan.io/tx/0xc255ddf225d7afe6a482a547e2f733d8c6177be60c236ef28fd2d52f282bc6e4#eventlog)
- EOA(0x2322ba43eFF1542b6A7bAeD35e66099Ea0d12Bd1): [added](https://etherscan.io/tx/0x9a81ede758b2687d3f55a124940d90ad37825b74015a9ef4a6a2620f1937b729#eventlog) → [removed](https://etherscan.io/tx/0x1e2911c96e75c2a594f220972a4c4c392deb69510322687dc811575a2715d32c#eventlog)
- Gnosis(0x41DFc53B13932a2690C9790527C1967d8579a6ae) 2/4: [added](https://etherscan.io/tx/0x184f5e7ab8bb03ed07990bb576e586ad4015e1472344287a85cdc5146361103f#eventlog)

### Group 8

- Can do following:
    - setAuthority(): [added](https://etherscan.io/tx/0x9936cb55ebdad7be0f764fdec6c28c5a8c28e4ed6b79025e0f74bdb6f52ca6f7#eventlog)
    - transferOwnership(): [added](https://etherscan.io/tx/0x31b5a2c32ed75b0cd41fa32d6c2cb4ee46dc0fb38b39e69ce664129c59054714#eventlog)
    - setBeforeTransferHook(): [added](https://etherscan.io/tx/0x8f103a4176f3c96457b95216241db3de8a850d31643317948582b1e5485ebd2a#eventlog)
    - AccountProvider.updateUpper/Lower(): [added](https://etherscan.io/tx/0xecab88f6e2a3330e9a9f3f022f8ce8181661e9c0fd1bdaa2b6a486ea81054be0#eventlog)
- EOA(0x2322ba43eFF1542b6A7bAeD35e66099Ea0d12Bd1): [added](https://etherscan.io/tx/0xf9d4d8f7418e8e6ca9062912fd37be988bcb41b5b9840d6f7fe2bc97013a0ff4#eventlog) → [removed](https://etherscan.io/tx/0x1e2911c96e75c2a594f220972a4c4c392deb69510322687dc811575a2715d32c#eventlog)
- Gnosis 0xCEA8039076E35a825854c5C2f85659430b06ec96: [added](https://etherscan.io/tx/0xb146dee52e52a9db67fbed7e3d7a93da4daf5c027790c35126ef78cbb6c035c3#eventlog)

### Group 9

- Can do following: Teller.removeAsset(): [added](https://etherscan.io/tx/0xf4b57b7e1f48a1687c5bbe76e1fd38a1c61a9012de9bd294d51bb524fb0008c1#eventlog)
- Gnosis(0xCEA8039076E35a825854c5C2f85659430b06ec96): [added](https://etherscan.io/tx/0xde14c3906ba28cae2bde747978b7bfa791876f998eb621f53f670b0d3c46cda7#eventlog)

### Group 10

- Can do following: Teller.refundDeposit(): [added](https://etherscan.io/tx/0x6d9de1c41157815cad25f3aacdd482c918cc7dff7027e1b3c80e684f860ecf20#eventlog)
- Gnosis(0x41DFc53B13932a2690C9790527C1967d8579a6ae) 2/4: [added](https://etherscan.io/tx/0xcc79c9ac20ad8d378c9873453003c337769e8a684394cf6b736148f42ce4996d#eventlog)

### Group 11

- Can do following: AccountRateProviders.updateExchangeRate(): [added](https://etherscan.io/tx/0xc0be893ff16a89f2bde0f81e7d6be36c2a64fa56767c96ac9fed70accd612b06#eventlog)
- Gnosis(0x41DFc53B13932a2690C9790527C1967d8579a6ae) 2/4: [added](https://etherscan.io/tx/0x05d010bb270f52d8dce073fb0738035eab69760bcc443054b626a740f1770dbe#eventlog)

### Group 12

- Can do following: Teller.bulkDeposit and Teller.bulkWithdraw: [added](https://etherscan.io/tx/0xf1533eb56e25019cdb5d46d290e025af2b4993248ff225e9b86d4827eba6ddfe#eventlog)
- AtomicSolverV3(0x989468982b08AEfA46E37CD0086142A86fa466D7): [added](https://etherscan.io/tx/0x3c89f8d1050fdb38d7ca689ff7e72bdcbb9a0e557d53a508f67bf142aac01cce#eventlog)

### Public access

- [Teller.deposit (0x0efe6a8b)](https://etherscan.io/address/0x221Ea02d409074546265CCD1123050F4D498ef64#writeContract#F4): [added](https://etherscan.io/tx/0xc51ae14f0a84f7d3f2b65b7d654836c79b47179325a2f7a1f5ecd411beb5d815#eventlog)
- [Teller.depositWithPermit (0x3d935d9e)](https://etherscan.io/address/0x221Ea02d409074546265CCD1123050F4D498ef64#writeContract#F5): [added](https://etherscan.io/tx/0xcfeb035b76cb1852dad323a792cf8af39699c36863876c44631f024187534eb0#eventlog)

## Function Signatures

### [BoringVault](https://etherscan.io/address/0x08c6F91e2B681FaF5e17227F2a44C307b3C1364C#code)

```solidity
bytes4(keccak256("manage(address,bytes,uint256)"))            = 0xf6e715d
bytes4(keccak256("manage(address[],bytes[],uint256[])"))      = 0x93c9e4d3
bytes4(keccak256("enter(address,address,uint256,address,uint256)")) = 0x39d6ba32
bytes4(keccak256("exit(address,address,uint256,address,uint256)"))  = 0x18457e61
bytes4(keccak256("setBeforeTransferHook(address)"))           = 0x8929565f
bytes4(keccak256("transfer(address,uint256)"))                = 0xa9059cbb
bytes4(keccak256("transferFrom(address,address,uint256)"))    = 0x23b872dd
```

### [Teller](https://etherscan.io/address/0x221Ea02d409074546265CCD1123050F4D498ef64#code)

```solidity
bytes4(keccak256("pause()"))                                  = 0x8456cb59
bytes4(keccak256("unpause()"))                                = 0x3f4ba83a
bytes4(keccak256("addAsset(address)"))                        = 0x298410e5
bytes4(keccak256("removeAsset(address)"))                     = 0x4a5e42b1
bytes4(keccak256("setShareLockPeriod(uint64)"))               = 0x12056e2d
bytes4(keccak256("beforeTransfer(address)"))                  = 0xd4ab4773
bytes4(keccak256("refundDeposit(uint256,address,address,uint256,uint256,uint256,uint256)")) = 0x285b929a
bytes4(keccak256("deposit(address,uint256,uint256)"))         = 0x0efe6a8b
bytes4(keccak256("depositWithPermit(address,uint256,uint256,uint256,uint8,bytes32,bytes32)")) = 0x9fd8ee41
bytes4(keccak256("bulkDeposit(address,uint256,uint256,address)"))        = 0x9d57442
bytes4(keccak256("bulkWithdraw(address,uint256,uint256,address)"))       = 0x3e64ce99
```

## Dune queries

### BulkWithdraw events from Teller contract

```sql
-- Simple query for BulkWithdraw events using only standard functions
SELECT
    block_time,
    tx_hash,
    contract_address,
    topic0 as event_signature,  -- Event signature
    topic1 as asset_address,  -- First indexed parameter (asset address)
    data as share_amount     -- Non-indexed parameter (shareAmount)
FROM ethereum.logs
WHERE contract_address = 0x221Ea02d409074546265CCD1123050F4D498ef64
-- BulkWithdraw event signature: keccak256("BulkWithdraw(address,uint256)")
AND topic0 = 0xdcc60b41ff1c604459e6aa4a7299817416b19fc586a392f111646e26597c4af9
ORDER BY block_time DESC
LIMIT 10
```

### ExchangeRateUpdated from AccountantWithRateProviders

```sql
-- Simple query for ExchangeRateUpdated events using only standard functions
SELECT
    block_time,
    tx_hash,
    contract_address,
    topic0 as event_signature,  -- Event signature
    varbinary_to_uint256(topic1) as old_rate,  -- First parameter (oldRate uint96)
    varbinary_to_uint256(topic2) as new_rate,  -- newRate
    varbinary_to_uint256(topic3) as current_time  -- currentTime
FROM ethereum.logs
WHERE contract_address = 0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7
-- BulkWithdraw event signature: keccak256("ExchangeRateUpdated(uint96,uint96,uint64)")
AND topic0 = 0xa95bc6aba40bbc4d95fc35f118c4cd8b53fc5d5b89ed264002af03503a7a9439
ORDER BY block_time DESC
LIMIT 10
```

### RoleCapabilityUpdated from AuthorityRoles

```sql
SELECT
    block_time,
    tx_hash,
    contract_address,
    topic0 as event_signature,  -- Event signature
    varbinary_to_uint256(topic1) as role_id,  -- role
    topic2 as target_address,  -- address target
    SUBSTRING(topic3 FROM 1 FOR 4)  as function_sig   -- bytes4 functionSig
FROM ethereum.logs
WHERE contract_address = 0xaBA6bA1E95E0926a6A6b917FE4E2f19ceaE4FF2e
-- RoleCapabilityUpdated event signature: keccak256("RoleCapabilityUpdated (index_topic_1 uint8 role, index_topic_2 address target, index_topic_3 bytes4 functionSig, bool enabled)")
AND topic0 = 0xa52ea92e6e955aa8ac66420b86350f7139959adfcc7e6a14eee1bd116d09860e
and varbinary_to_uint256(topic1) = 4 -- Group 4 or remove for all
ORDER BY block_time DESC
LIMIT 10
```

### UserRoleUpdated from AuthorityRoles

```sql
-- Simple query for UserRoleUpdated events using only standard functions
SELECT
    block_time,
    tx_hash,
    contract_address,
    topic0 as event_signature,  -- Event signature
    topic1 as user_address,  -- address user
    varbinary_to_uint256(topic2) as role_id,  -- uint8 role
    topic3 as enabled_flag  -- enabled
FROM ethereum.logs
WHERE contract_address = 0xaBA6bA1E95E0926a6A6b917FE4E2f19ceaE4FF2e
-- UserRoleUpdated event signature: keccak256("UserRoleUpdated (index_topic_1 address user, index_topic_2 uint8 role, bool enabled)")
AND topic0 = 0x4c9bdd0c8e073eb5eda2250b18d8e5121ff27b62064fbeeeed4869bb99bc5bf2
ORDER BY block_time DESC
LIMIT 10
```

### BoringVaultManaged from ManagerWithMerkleVerification

```sql
-- Simple query for BoringVaultManaged events using only standard functions
SELECT
    block_time,
    tx_hash,
    contract_address,
    topic0 as event_signature,  -- Event signature
    topic1 as calls_made  -- callsMade
FROM ethereum.logs
WHERE contract_address = 0xcff411d5c54fe0583a984bee1ef43a4776854b9a
-- BoringVaultManaged event signature: keccak256("BoringVaultManaged(uint256)")
AND topic0 = 0x53d426e7d80bb2c8674d3b45577e2d464d423faad6531b21f95ac11ac18b1cb6
ORDER BY block_time DESC
LIMIT 10
```
