import { ChainContracts } from "../peggedAsset.type";

export const chainContracts: ChainContracts = {
  ethereum: {
    issued: ["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"],
    unreleased: ["0x55fe002aeff02f77364de339a1292923a15844b8"],
    bridgedFromBSC: ["0x7cd167B101D2808Cfd2C45d17b2E7EA9F46b74B6"],
  },
  polygon: {
    issued: ["0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"],
    bridgeOnETH: ["0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf"],
    bridgedFromETH: [
      "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
      "0x4318cb63a2b8edf2de971e2f17f77097e499459d",
    ],
  },
  bsc: {
    bridgeOnETH: ["0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503"],
    bridgedFromETH18: ["0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"],
  },
  arbitrum: {
    issued: ["0xaf88d065e77c8cc2239327c5edb3a432268e5831"],
    bridgeOnETH: ["0xcee284f754e854890e311e3280b767f80797180d"],
    bridgedFromETH: ["0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"],
  },
};
