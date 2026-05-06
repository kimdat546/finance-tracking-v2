# Security Notice — Malware Cleanup (2026-05-06)

This repository was infected with the [PolinRider](https://opensourcemalware.com/blog/polinrider-attack) supply-chain malware (DPRK / Lazarus group) sometime in April 2026.

The malware appended an obfuscated JavaScript payload to a config or entry-point file in this repo. As of **2026-05-06** the malware has been surgically removed from all branches and history via `git filter-repo`. **All commit SHAs from before this date have changed.**

## If you cloned this repo before 2026-05-06

1. Delete your local clone.
2. Re-clone fresh from GitHub.
3. If you executed `npm install` / `pnpm install` / `yarn`, or any build / dev script while running infected code, audit your local machine — the payload tries to steal credentials and propagate to other repos.

## Detection markers

The malicious payload was appended to one of: `postcss.config.mjs`, `tailwind.config.js`, `tailwind.config.ts`, `eslint.config.js`, `eslint.config.mjs`, `vite.config.js`, `next.config.mjs`, `webpack.config.js`, `App.js`, `index.js`, `index.ts`, `server.js`, `.assetpack.js`, or scripts in `scripts/`.

Strings to grep for: `rmcej%otb%`, `Cot%3t=shtP`, `_$_1e42`, `global['!']`, `global['_V']`, `default-configuration.vercel.app`, `260120.vercel.app`.

## References

- [OpenSourceMalware PolinRider analysis](https://opensourcemalware.com/blog/polinrider-attack)
- [PolinRider IOC repository](https://github.com/OpenSourceMalware/PolinRider)
- [The Invisible Patch — git history rewriting analysis](https://securityonline.info/polinrider-dprk-malware-github-history-falsification/)
- [Wiz threats incident page](https://threats.wiz.io/all-incidents/polinrider-supply-chain-attack)
