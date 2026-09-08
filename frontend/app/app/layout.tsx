import type { ReactNode } from "react";
import { ProductChrome } from "../components/ProductChrome";

export default function ProductLayout({ children }: { children: ReactNode }) {
  return <ProductChrome>{children}</ProductChrome>;
}
