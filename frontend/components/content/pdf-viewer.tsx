"use client";

/**
 * PDF Viewer Component (E2.2, TA-E2.2-01, TA-E2.2-02)
 *
 * Displays PDF with inline embed for supported browsers and fallback for iOS/Safari.
 * Features:
 * - Inline PDF embed via <object> tag for desktop browsers
 * - Direct links fallback for iOS Safari and in-app browsers
 * - Sticky download bar with file details
 * - Responsive design
 */

import { useEffect, useState } from "react";
import { Download, ExternalLink, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

// User agent patterns for unsupported browsers
const IOS_SAFARI_PATTERN = /iPhone|iPad|iPod/i;
const IOS_BROWSER_PATTERN = /CriOS|FxiOS/i; // Chrome/Firefox on iOS
const IN_APP_BROWSER_PATTERN = /FBAN|FBAV|Instagram|Twitter|LinkedIn/i;

interface PDFViewerProps {
  /** URL for PDF viewing */
  embedUrl: string;
  /** URL for PDF download (with ?download=1) */
  downloadUrl: string;
  /** Filename for download */
  filename: string;
  /** File size display string (e.g., "2.5 MB") */
  fileSizeDisplay?: string;
  /** Page count display string (e.g., "12 pages") */
  pageCountDisplay?: string;
  /** Height of the embed viewer */
  height?: string;
  /** Optional CSS class */
  className?: string;
}

/**
 * Detect if the browser supports inline PDF embedding.
 * Returns [supports, reason] tuple.
 */
function detectPdfEmbedSupport(): [boolean, string | null] {
  if (typeof window === "undefined") {
    // SSR: assume support, client will re-check
    return [true, null];
  }

  const ua = navigator.userAgent;

  // iOS Safari and all iOS browsers use WebKit which doesn't support PDF embed
  if (IOS_SAFARI_PATTERN.test(ua)) {
    return [false, "iOS Safari doesn't support inline PDF viewing. Use the links below."];
  }

  // iOS Chrome/Firefox also use WebKit
  if (IOS_BROWSER_PATTERN.test(ua)) {
    return [false, "iOS browsers don't support inline PDF viewing. Use the links below."];
  }

  // In-app browsers (Facebook, Instagram, Twitter, LinkedIn)
  if (IN_APP_BROWSER_PATTERN.test(ua)) {
    return [false, "In-app browsers don't support inline PDF viewing. Open in your browser."];
  }

  return [true, null];
}

/**
 * Format file details for display
 */
function formatFileDetails(
  fileSizeDisplay?: string,
  pageCountDisplay?: string
): string {
  const parts = [];
  if (fileSizeDisplay) parts.push(fileSizeDisplay);
  if (pageCountDisplay) parts.push(pageCountDisplay);
  return parts.join(" · ");
}

export function PDFViewer({
  embedUrl,
  downloadUrl,
  filename,
  fileSizeDisplay,
  pageCountDisplay,
  height = "600px",
  className = "",
}: PDFViewerProps) {
  const [supportsEmbed, setSupportsEmbed] = useState(true);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Detect browser support on mount
  useEffect(() => {
    setMounted(true);
    const [supports, reason] = detectPdfEmbedSupport();
    setSupportsEmbed(supports);
    setFallbackReason(reason);
  }, []);

  const fileDetails = formatFileDetails(fileSizeDisplay, pageCountDisplay);

  // Show loading state during SSR hydration
  if (!mounted) {
    return (
      <div className={`pdf-viewer ${className}`}>
        <div className="bg-muted rounded-lg flex items-center justify-center" style={{ height }}>
          <FileText className="w-12 h-12 text-muted-foreground animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className={`pdf-viewer ${className}`}>
      {/* PDF Embed or Fallback */}
      {supportsEmbed ? (
        <object
          data={embedUrl}
          type="application/pdf"
          width="100%"
          style={{ height }}
          className="rounded-lg border"
          aria-label={`PDF viewer for ${filename}`}
        >
          {/* Fallback inside object tag for browsers that fail to load */}
          <div className="bg-muted rounded-lg p-8 flex flex-col items-center justify-center gap-4" style={{ height }}>
            <FileText className="w-12 h-12 text-muted-foreground" />
            <p className="text-muted-foreground text-center">
              Your browser doesn&apos;t support embedded PDFs.
            </p>
            <div className="flex gap-3">
              <Button asChild variant="default">
                <a href={embedUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Open in New Tab
                </a>
              </Button>
              <Button asChild variant="outline">
                <a href={downloadUrl} download={filename}>
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </a>
              </Button>
            </div>
          </div>
        </object>
      ) : (
        /* Direct fallback for iOS/Safari/in-app browsers */
        <div className="bg-muted rounded-lg p-8 flex flex-col items-center justify-center gap-4" style={{ height }}>
          <FileText className="w-16 h-16 text-muted-foreground" />
          <p className="text-muted-foreground text-center max-w-md">
            {fallbackReason || "PDF preview not available on this device."}
          </p>
          <div className="flex gap-3 flex-wrap justify-center">
            <Button asChild variant="default">
              <a href={embedUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                Open PDF in New Tab
              </a>
            </Button>
            <Button asChild variant="outline">
              <a href={downloadUrl} download={filename}>
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </a>
            </Button>
          </div>
        </div>
      )}

      {/* Sticky Download Bar */}
      <div className="sticky bottom-0 mt-4 bg-background/95 backdrop-blur border rounded-lg p-3 flex items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center gap-3 min-w-0">
          <FileText className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <div className="min-w-0">
            <p className="font-medium truncate">{filename}</p>
            {fileDetails && (
              <p className="text-sm text-muted-foreground">{fileDetails}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Button asChild variant="ghost" size="sm">
            <a href={embedUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4 mr-1" />
              Open
            </a>
          </Button>
          <Button asChild variant="default" size="sm">
            <a href={downloadUrl} download={filename}>
              <Download className="w-4 h-4 mr-1" />
              Download
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}

export default PDFViewer;
