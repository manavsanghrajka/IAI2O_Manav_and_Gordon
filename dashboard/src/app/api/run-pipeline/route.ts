import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

/**
 * POST /api/run-pipeline
 * Triggers the Python AI pipeline via Docker Compose.
 * Falls back to direct Python execution if Docker is unavailable.
 */
export async function POST() {
  const projectRoot = path.join(process.cwd(), "..");

  try {
    // Try Docker Compose first
    try {
      const { stdout, stderr } = await execAsync(
        "docker compose run --rm ai-mechanistic-model",
        {
          cwd: projectRoot,
          timeout: 600000, // 10 minute timeout
        }
      );
      
      return NextResponse.json({
        success: true,
        method: "docker",
        output: stdout,
        warnings: stderr || undefined,
      });
    } catch (dockerError) {
      console.log("Docker not available, trying direct Python execution...");
      
      // Fallback: Try running Python directly
      const { stdout, stderr } = await execAsync(
        "python src/main.py",
        {
          cwd: projectRoot,
          timeout: 600000,
        }
      );
      
      return NextResponse.json({
        success: true,
        method: "python",
        output: stdout,
        warnings: stderr || undefined,
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      {
        success: false,
        error: message,
        hint: "Ensure Docker is running or Python with dependencies is installed. Run: pip install -r requirements.txt",
      },
      { status: 500 }
    );
  }
}
