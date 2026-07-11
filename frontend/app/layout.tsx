import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Village — 거울 클론 라이프시뮬",
  description: "블라인드 처리된 과거 실제 코인 시장에서, 나를 복제한 클론이 대신 산다",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-white text-black">{children}</body>
    </html>
  );
}
