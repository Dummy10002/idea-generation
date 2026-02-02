require('dotenv').config();
const fs = require('fs');
const { Client } = require('@notionhq/client');
const { markdownToBlocks } = require('@tryfabric/martian');

// --- Configuration ---
// Retrieve environment variables
const NOTION_TOKEN = process.env.NOTION_TOKEN;
const DATABASE_ID = process.env.NOTION_DATABASE_ID;

// Validate configuration
if (!NOTION_TOKEN) {
    console.error("❌ Error: NOTION_TOKEN not found in environment variables.");
    console.log("Please check your .env file.");
    process.exit(1);
}

if (!DATABASE_ID) {
    console.error("❌ Error: NOTION_DATABASE_ID not found in environment variables.");
    console.log("Please check your .env file.");
    process.exit(1);
}

// Initialize Notion Client
const notion = new Client({ auth: NOTION_TOKEN });

/**
 * Helper to extract a title from markdown blocks or content
 */
function extractTitle(blocks) {
    // Try to find the first heading_1 block
    const titleBlock = blocks.find(b => b.type === 'heading_1');
    if (titleBlock && titleBlock.heading_1.rich_text.length > 0) {
        return titleBlock.heading_1.rich_text.map(t => t.plain_text).join('');
    }
    return "New Markdown Import"; // Default title
}

/**
 * Main function to convert Markdown and create a new page in Notion Database
 * @param {string} markdownContent - The markdown string to convert
 */
async function appendMarkdownToNotion(markdownContent) {
    console.log("🔄 Starting conversion...");

    try {
        // 1. Convert Markdown to Notion Blocks
        const blocks = markdownToBlocks(markdownContent);

        console.log(`✅ Successfully converted markdown to ${blocks.length} Notion blocks.`);

        // 2. Prepare Title and Content
        // We extract the first H1 to be the page title in the database
        const title = extractTitle(blocks);

        // Remove the title block from the content if we used it as the page title (optional, but cleaner)
        // const contentBlocks = blocks.filter(b => b.type !== 'heading_1' || b !== blocks.find(x => x.type === 'heading_1'));
        // Keeping it simple: Send all blocks as content as well, or strip the first one.
        // Let's strip the first H1 if it matches the title to avoid duplication
        const contentBlocks = blocks.length > 0 && blocks[0].type === 'heading_1' ? blocks.slice(1) : blocks;

        console.log(`📤 Creating new page in Database ID: ${DATABASE_ID}`);
        console.log(`   Title: "${title}"`);

        // 3. Create the Page in the Database
        const response = await notion.pages.create({
            parent: { database_id: DATABASE_ID },
            properties: {
                Title: { // Ensure your database has a 'Title' property (standard name is 'Name' or 'Title')
                    title: [
                        {
                            text: {
                                content: title,
                            },
                        },
                    ],
                },
                // Add other properties here if needed, e.g., Date, Source, etc.
            },
            children: contentBlocks,
        });

        console.log("🎉 Success! New page created in Notion database.");
        console.log(`   Page URL: ${response.url}`);

    } catch (error) {
        console.error("❌ Error processing request:");
        if (error.code === 'object_not_found') {
            console.error(`   The Database ID '${DATABASE_ID}' was not found. Ensure the ID is correct and the integration has access to the database.`);
        } else if (error.code === 'unauthorized') {
            console.error("   Authentication failed. Check your NOTION_TOKEN.");
        } else if (error.message.includes('property')) {
            console.error("   Property error: Ensure your database has a standard 'Title' property.");
            console.error("   " + error.message);
        } else {
            console.error(error.message || error);
        }
        process.exit(1);
    }
}

// --- Usage / Execution ---

// Example Markdown input from requirements
const exampleMarkdown = `
# 🔥 Top Community Debates (Daily Digest)

*4 trending discussions found across Reddit, X, and HackerNews.*

---

## 🔴 Reddit

**Discussion Title**

Description text here.

🔗 [View Discussion](https://example.com)
`;

// Determine source of markdown: Command line argument (file path) or default example
const args = process.argv.slice(2);
let contentToProcess = exampleMarkdown;

if (args.length > 0) {
    const filePath = args[0];
    try {
        if (fs.existsSync(filePath)) {
            console.log(`📄 Reading markdown from file: ${filePath}`);
            contentToProcess = fs.readFileSync(filePath, 'utf8');
        } else {
            console.warn(`⚠️ File not found: ${filePath}. Using example content instead.`);
        }
    } catch (err) {
        console.error(`❌ Error reading file: ${err.message}`);
        process.exit(1);
    }
} else {
    console.log("ℹ️ No file argument provided. Using default example markdown.");
}

// Run the function
appendMarkdownToNotion(contentToProcess);
