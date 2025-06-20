#!/bin/bash

# === DevSuite Single-File Builder ===
# Combines the modular DevSuite scripts into one executable Bash script.

set -euo pipefail

# --- Configuration ---
SOURCE_DIR="./devsuite"
SCRIPTS_SUBDIR="scripts"
LAUNCHER_SCRIPT="devsuite.sh"
OUTPUT_SCRIPT="DevSuite_standalone.sh"
COMMON_SCRIPT_NAME="_common.sh" # Optional common functions script

# --- Validation ---
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: Source directory '$SOURCE_DIR' not found." >&2
    exit 1
fi
if [[ ! -f "$SOURCE_DIR/$LAUNCHER_SCRIPT" ]]; then
    echo "Error: Launcher script '$SOURCE_DIR/$LAUNCHER_SCRIPT' not found." >&2
    exit 1
fi
if [[ ! -d "$SOURCE_DIR/$SCRIPTS_SUBDIR" ]]; then
    echo "Error: Scripts subdirectory '$SOURCE_DIR/$SCRIPTS_SUBDIR' not found." >&2
    exit 1
fi

echo "Starting build process for $OUTPUT_SCRIPT..."

# --- Start Output Script ---
cat << EOF > "$OUTPUT_SCRIPT"
#!/bin/bash
# Standalone DevSuite - Generated on $(date)
# Combines launcher and all modules from $SOURCE_DIR

set -euo pipefail

# --- Embedded Common Functions (if _common.sh exists) ---
EOF

# --- Embed Common Script (Optional) ---
COMMON_SCRIPT_PATH="$SOURCE_DIR/$SCRIPTS_SUBDIR/$COMMON_SCRIPT_NAME"
if [[ -f "$COMMON_SCRIPT_PATH" ]]; then
    echo "Embedding common functions from $COMMON_SCRIPT_NAME..."
    # Append content, skipping shebang if present
    sed '1{/^#!/d;}' "$COMMON_SCRIPT_PATH" >> "$OUTPUT_SCRIPT"
    echo "" >> "$OUTPUT_SCRIPT" # Add a newline for separation
fi

# --- Embed Tool Scripts as Functions ---
echo "# --- Embedded Tool Script Functions ---" >> "$OUTPUT_SCRIPT"
SCRIPT_FILES=("$SOURCE_DIR/$SCRIPTS_SUBDIR"/*.sh)

# Exclude common script from this loop if it exists
if [[ -f "$COMMON_SCRIPT_PATH" ]]; then
     TEMP_FILES=()
     for file in "${SCRIPT_FILES[@]}"; do
         if [[ "$(basename "$file")" != "$COMMON_SCRIPT_NAME" ]]; then
             TEMP_FILES+=("$file")
         fi
     done
     SCRIPT_FILES=("${TEMP_FILES[@]}")
fi


declare -A function_map # Map script basename to function name

for script_path in "${SCRIPT_FILES[@]}"; do
    script_basename=$(basename "$script_path")
    # Sanitize basename to create a valid function name
    # Replace hyphens, dots with underscores, remove .sh extension
    func_name="run_$(echo "$script_basename" | sed 's/\.sh$//; s/[-.]/_/g')"

    echo "Embedding $script_basename as function $func_name()..."
    function_map["$script_basename"]="$func_name"

    echo "function $func_name() {" >> "$OUTPUT_SCRIPT"
    # Append script content, skipping shebang
    sed '1{/^#!/d;}' "$script_path" >> "$OUTPUT_SCRIPT"
    echo "" >> "$OUTPUT_SCRIPT" # Add newline before closing brace
    echo "}" >> "$OUTPUT_SCRIPT"
    echo "" >> "$OUTPUT_SCRIPT" # Add newline for separation
done

# --- Embed Main Launcher Logic ---
echo "# --- Main Launcher Logic ---" >> "$OUTPUT_SCRIPT"
LAUNCHER_CONTENT=$(cat "$SOURCE_DIR/$LAUNCHER_SCRIPT")

# Modify the case statement in the launcher content to call functions
MODIFIED_LAUNCHER_CONTENT="$LAUNCHER_CONTENT"
for script_basename in "${!function_map[@]}"; do
    func_name="${function_map[$script_basename]}"
    # Escape for sed: characters like /, &, \
    escaped_script_path=$(printf '%s\n' "$SCRIPTS_SUBDIR/$script_basename" | sed 's:[][\\/.^$*]:\\&:g')
    # Look for lines like: bash "$TOOL_SCRIPTS_PATH/script.sh" OR bash "./scripts/script.sh" (adjust regex if needed)
    # Replace with the function call. Use pipe delimiter for sed paths.
    MODIFIED_LAUNCHER_CONTENT=$(echo "$MODIFIED_LAUNCHER_CONTENT" | sed "s|bash \"\$TOOL_SCRIPTS_PATH/$escaped_script_path\"|$func_name|g")
    # Also handle potential variations like direct relative paths if TOOL_SCRIPTS_PATH wasn't used consistently
    MODIFIED_LAUNCHER_CONTENT=$(echo "$MODIFIED_LAUNCHER_CONTENT" | sed "s|bash \"\./$escaped_script_path\"|$func_name|g")

done

# Append the modified launcher content, skipping its shebang
echo "$MODIFIED_LAUNCHER_CONTENT" | sed '1{/^#!/d;}' >> "$OUTPUT_SCRIPT"

# --- Make Executable ---
chmod +x "$OUTPUT_SCRIPT"

echo "Build complete! Standalone script created: $OUTPUT_SCRIPT"
echo "You can now run it directly: ./$OUTPUT_SCRIPT"

exit 0
