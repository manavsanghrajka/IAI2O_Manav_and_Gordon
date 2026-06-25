import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

/**
 * POST /api/run-pipeline
 * Triggers the PowerShell pipeline.
 */
export async function POST() {
  const projectRoot = path.join(process.cwd(), "..");

  try {
    const { stdout, stderr } = await execAsync(
      "powershell -ExecutionPolicy Bypass -File ./run_global_pipeline.ps1",
      {
        cwd: projectRoot,
        timeout: 600000,
      }
    );
    
    return NextResponse.json({
      success: true,
      method: "powershell",
      output: stdout,
      warnings: stderr || undefined,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      {
        success: false,
        error: message,
        hint: "Ensure PowerShell is available and Python is in your PATH.",
      },
      { status: 500 }
    );
  }
}
