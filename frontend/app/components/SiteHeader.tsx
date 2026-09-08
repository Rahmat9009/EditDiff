"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { API_BASE } from "../lib/api";

type Props = {
  /** Omitted on the landing page, where API reachability is not the point. */
  apiOnline?: boolean | null;
};

const NAV = [
  { href: "/app/compare", label: "Compare" },
  { href: "/app/release-gate", label: "Release Gate" },
];

export function SiteHeader({ apiOnline }: Props) {
  const pathname = usePathname();
  const showChip = apiOnline !== undefined;
  const label = apiOnline === null ? "Checking API" : apiOnline ? "API online" : "API offline";
  const state = apiOnline === null ? "pending" : apiOnline ? "online" : "offline";

  return (
    <header className="masthead">
      <div className="shell masthead__inner">
        <Link className="brand" href="/">
          {/* Official mark, recoloured to the shipped palette. Fixed box so the
              masthead height never shifts while the image loads. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="brand__mark"
            src="/brand/editdiff-mark.png"
            alt=""
            width={40}
            height={40}
            decoding="async"
          />
          <span className="brand__name">EditDiff</span>
          <span className="brand__claim">Regression testing for video production.</span>
        </Link>

        <nav className="nav" aria-label="Product">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav__link${active ? " is-active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {showChip ? (
          <p className={`api-chip api-chip--${state}`} title={API_BASE}>
            <span className="api-chip__dot" aria-hidden="true" />
            {label}
          </p>
        ) : null}
      </div>
    </header>
  );
}
