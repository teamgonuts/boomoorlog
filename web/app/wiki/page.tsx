import { redirect } from "next/navigation";

// /wiki is reserved as a future hub for wiki sections (trees, ZIPs, battles).
// For now it sends visitors to the only section that exists.
export default function WikiIndex() {
  redirect("/wiki/trees");
}
