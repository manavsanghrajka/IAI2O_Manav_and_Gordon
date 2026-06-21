import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

/**
 * GET /api/data
 * Reads dashboard_data.json from the project data/ directory.
 */
export async function GET() {
  try {
    // We assume the Next.js app is run from `dashboard/`
    const dataPath = path.join(process.cwd(), "..", "data", "exports", "dashboard_data.json");
    
    const fileContent = await readFile(dataPath, "utf-8");
    const data = JSON.parse(fileContent);
    
    return NextResponse.json(data);
  } catch (error) {
    // File not found — no data generated yet
    if (error instanceof Error && "code" in error && (error as NodeJS.ErrnoException).code === "ENOENT") {
      return NextResponse.json(
        { error: "Dashboard data not found. Run the pipeline first." },
        { status: 404 }
      );
    }
    
    return NextResponse.json(
      { error: `Failed to load data: ${error instanceof Error ? error.message : "Unknown error"}` },
      { status: 500 }
    );
  }
}
