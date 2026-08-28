import { ChainContracts } from "../peggedAsset.type";

export const chainContracts: ChainContracts = {
  ethereum: {
    issued: ["0xdac17f958d2ee523a2206206994597c13d831ec7"],
    bridgedFromBSC: ["0x667120b501267010DaE1788889AcF1d647D681d0"],
  },
  polygon: {
    bridgedFromETH: ["0xc2132d05d31c914a87c6611c10748aeb04b58e8f"],
    bridgeOnETH: ["0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf"],
  },
  tron: {
    issued: ["TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"],
  },
};
