/**
 * Help Center Content Data Structure
 * Categories and articles for the help center page
 */

export interface HelpArticle {
	category: string;
	title: string;
	slug: string;
	content: string;
	keywords: string[];
}

export interface HelpCategory {
	id: string;
	label: string;
	icon: string;
}

export const helpCategories: HelpCategory[] = [
	{ id: 'getting-started', label: 'Getting Started', icon: 'rocket' },
	{ id: 'meetings', label: 'Meetings', icon: 'users' },
	{ id: 'actions', label: 'Actions', icon: 'check-circle' },
	{ id: 'datasets', label: 'Datasets', icon: 'database' },
	{ id: 'settings', label: 'Settings', icon: 'settings' },
	{ id: 'troubleshooting', label: 'Troubleshooting', icon: 'help-circle' },
];

export const helpArticles: HelpArticle[] = [
	// Getting Started
	{
		category: 'getting-started',
		title: 'Your First Meeting',
		slug: 'first-meeting',
		content: `## Running Your First Meeting

Board of One helps you make better decisions by assembling a virtual board of expert advisors tailored to your question.

### How to Start

1. Click **New Meeting** in the header
2. Enter your business question or decision you need to make
3. Optionally add business context to help the experts understand your situation
4. Click **Start Meeting** to begin

### What Happens Next

The system will:
- Analyze your question and break it into key focus areas
- Select 3-5 expert personas relevant to your question
- Run a structured deliberation where experts share perspectives
- Synthesize their insights into actionable recommendations

### Tips for Better Results

- Be specific about what decision you're trying to make
- Include relevant constraints (budget, timeline, resources)
- Mention any options you're already considering`,
		keywords: ['start', 'begin', 'first', 'new', 'create', 'how to', 'tutorial'],
	},
	{
		category: 'getting-started',
		title: 'Setting Up Business Context',
		slug: 'business-context',
		content: `## Business Context

Providing business context helps the expert advisors give you more relevant, actionable advice tailored to your specific situation.

### What to Include

- **Industry**: What sector you operate in
- **Company Stage**: Startup, growth, established
- **Team Size**: Number of employees or team members
- **Key Metrics**: Revenue, users, or other relevant numbers
- **Current Challenges**: What you're working on

### How to Add Context

1. Go to **Settings** > **Context**
2. Fill in the relevant fields
3. Save your changes

Your context is automatically included in future meetings to provide better recommendations.

### Privacy Note

Your business context is stored securely and only used to improve the quality of advice. You can edit or delete it at any time.`,
		keywords: ['context', 'business', 'setup', 'configure', 'profile', 'company', 'industry'],
	},
	{
		category: 'getting-started',
		title: 'Understanding Expert Personas',
		slug: 'expert-personas',
		content: `## Expert Personas

Board of One assembles a virtual advisory board of expert personas for each meeting. Each persona brings a different perspective to your decision.

### How Experts Are Selected

The system analyzes your question and selects 3-5 relevant experts from categories like:

- **Strategic Thinkers**: Business strategy, market analysis
- **Technical Experts**: Engineering, technology decisions
- **Financial Advisors**: Budgeting, ROI analysis
- **Operations Specialists**: Process optimization, logistics
- **Customer Advocates**: User experience, market fit

### During the Meeting

Each expert:
- Reviews your question and context
- Shares their perspective in multiple rounds
- Responds to and builds on other experts' insights
- Contributes to the final recommendations

### The Facilitator

A facilitator guides the discussion, ensuring all perspectives are heard and the meeting stays productive.`,
		keywords: ['experts', 'personas', 'advisors', 'board', 'virtual', 'ai'],
	},

	// Meetings
	{
		category: 'meetings',
		title: 'Creating a Meeting',
		slug: 'create-meeting',
		content: `## Creating a Meeting

Meetings are the core of Board of One. Each meeting addresses a specific question or decision.

### Steps to Create

1. Click **New Meeting** in the header
2. Enter your question in the text area
3. Optionally attach a dataset for data-driven insights
4. Click **Start Meeting**

### Pre-Meeting Questions

Before experts deliberate, you may be asked clarifying questions to ensure the advice is relevant. These help establish:

- Constraints and requirements
- Current situation details
- Decision criteria

You can skip these if you prefer to get straight to deliberation.

### Meeting Duration

Most meetings take 2-5 minutes to complete, depending on complexity.`,
		keywords: ['create', 'new', 'start', 'question', 'decision', 'deliberation'],
	},
	{
		category: 'meetings',
		title: 'Sub-Problems and Focus Areas',
		slug: 'sub-problems',
		content: `## Sub-Problems and Focus Areas

For complex questions, Board of One may break your question into multiple focus areas (sub-problems) to ensure thorough analysis.

### How It Works

1. Your main question is analyzed
2. Key themes or aspects are identified
3. Each becomes a separate "focus area" with dedicated discussion
4. Results are synthesized into unified recommendations

### Example

**Question**: "Should we expand into the European market?"

**Focus Areas**:
- Market opportunity and competition
- Regulatory and compliance requirements
- Resource and operational implications

### Viewing Focus Areas

During a meeting, use the tabs above the discussion to switch between focus areas and see the specific insights for each.`,
		keywords: ['sub-problems', 'focus', 'areas', 'decomposition', 'complex', 'breakdown'],
	},
	{
		category: 'meetings',
		title: 'Reading the Synthesis',
		slug: 'synthesis',
		content: `## Understanding the Synthesis

After experts deliberate, the system produces a synthesis combining their perspectives into actionable recommendations.

### Synthesis Structure

- **Executive Summary**: Key takeaways at a glance
- **Recommendations**: Specific actions to consider
- **Risk Analysis**: Potential concerns and mitigations
- **Next Steps**: Suggested immediate actions

### Expert Perspectives

The synthesis shows where experts agreed and disagreed, helping you understand the full range of considerations.

### Actions

Actionable items from the synthesis can be converted to tracked actions with due dates and status.`,
		keywords: ['synthesis', 'summary', 'recommendations', 'results', 'output', 'conclusion'],
	},

	// Actions
	{
		category: 'actions',
		title: 'Tracking Actions',
		slug: 'tracking-actions',
		content: `## Tracking Actions

Actions are tasks that emerge from meeting recommendations. Track them to ensure follow-through on decisions.

### Action Properties

- **Title**: What needs to be done
- **Status**: To Do, In Progress, Done, Blocked
- **Priority**: Low, Medium, High, Urgent
- **Due Date**: When it should be completed
- **Source Meeting**: Which meeting generated this action

### Managing Actions

1. Go to **Work** > **Actions** in the navigation
2. View all actions across meetings
3. Filter by status, due date, or meeting
4. Click an action to view details or update status

### Bulk Operations

Select multiple actions using checkboxes to:
- Mark as complete
- Change status
- Update priority`,
		keywords: ['actions', 'tasks', 'todo', 'track', 'follow-up', 'manage'],
	},
	{
		category: 'actions',
		title: 'Gantt Chart View',
		slug: 'gantt-view',
		content: `## Gantt Chart View

The Gantt chart provides a timeline view of your actions, helping you visualize workload and deadlines.

### Accessing the Gantt View

1. Go to **Work** > **Actions**
2. Click the **Gantt** tab

### Features

- **Timeline**: See actions laid out by start and due dates
- **Drag to Reschedule**: Move action bars to change dates
- **Dependencies**: View which actions depend on others
- **Zoom**: Switch between day, week, and month views

### Tips

- Use the Gantt view to spot scheduling conflicts
- Identify gaps in your planning
- Balance workload across time periods`,
		keywords: ['gantt', 'timeline', 'chart', 'schedule', 'planning', 'calendar'],
	},

	// Datasets
	{
		category: 'datasets',
		title: 'Uploading Data',
		slug: 'upload-data',
		content: `## Uploading Datasets

Add datasets to get data-driven insights during meetings or use the Q&A feature for direct analysis.

### Supported Formats

- **CSV files**: Drag and drop or click to upload
- **Google Sheets**: Paste a public sheet URL

### Upload Process

1. Go to **Data** > **Datasets**
2. Drag a CSV file onto the upload area, or
3. Paste a Google Sheets URL and click **Import**

### Data Profiling

After upload, the system automatically:
- Detects column types (dates, numbers, text)
- Calculates statistics (min, max, averages)
- Generates a summary of your data

### Size Limits

- Maximum file size: 10MB
- Maximum rows: 100,000 for standard analysis`,
		keywords: ['upload', 'csv', 'data', 'import', 'google sheets', 'file'],
	},
	{
		category: 'datasets',
		title: 'Ask Questions About Your Data',
		slug: 'data-qa',
		content: `## Dataset Q&A

Ask natural language questions about your uploaded datasets and get AI-powered analysis.

### How to Use

1. Go to **Data** > **Datasets**
2. Click on a dataset to open it
3. Type your question in the chat interface
4. View the analysis and any generated charts

### Example Questions

- "What are the top 5 products by revenue?"
- "Show me the trend in monthly sales"
- "Which regions have the highest growth rate?"
- "Compare Q1 vs Q2 performance"

### Charts and Visualizations

The system can generate:
- Bar charts
- Line charts
- Pie charts
- Scatter plots

Charts are saved to your analysis history for future reference.`,
		keywords: ['ask', 'question', 'query', 'analysis', 'chat', 'qa', 'charts'],
	},
	{
		category: 'datasets',
		title: 'Using Data in Meetings',
		slug: 'data-in-meetings',
		content: `## Data-Driven Meetings

Attach datasets to meetings so experts can reference your actual data in their analysis.

### Attaching a Dataset

1. When creating a new meeting, click **Attach Dataset**
2. Select from your uploaded datasets
3. Proceed with your question

### How Experts Use Data

With a dataset attached, experts can:
- Reference specific metrics and trends
- Base recommendations on actual numbers
- Identify data-driven opportunities and risks

### Best Practices

- Ensure your dataset is relevant to the question
- Include recent data for timely insights
- Consider what columns/metrics matter most`,
		keywords: ['data', 'dataset', 'attach', 'meeting', 'analysis', 'metrics'],
	},

	// Settings
	{
		category: 'settings',
		title: 'Account Settings',
		slug: 'account-settings',
		content: `## Account Settings

Manage your account preferences and profile information.

### Accessing Settings

Click **Settings** in the navigation to access:

- **Account**: Email, password, display name
- **Context**: Business context and preferences
- **Privacy**: Data export, retention, deletion

### Changing Email

1. Go to **Settings** > **Account**
2. Enter your new email address
3. Verify via the confirmation email sent

### Password Changes

Password changes are handled through the secure authentication flow. Click "Change Password" to receive a reset link.`,
		keywords: ['account', 'profile', 'email', 'password', 'preferences'],
	},
	{
		category: 'settings',
		title: 'Privacy and Data',
		slug: 'privacy-data',
		content: `## Privacy and Data Management

Board of One gives you full control over your data.

### Data Export

Export all your data (meetings, actions, context) in JSON format:

1. Go to **Settings** > **Privacy**
2. Click **Export My Data**
3. Download the generated file

Note: You can request an export once every 24 hours.

### Data Retention

Choose how long your meeting data is retained:
- Default: 365 days
- Configure from 30 to 730 days

### Account Deletion

To permanently delete your account and all data:

1. Go to **Settings** > **Privacy**
2. Click **Delete Account**
3. Confirm by typing your email
4. All data is anonymized and removed

This action is irreversible.`,
		keywords: ['privacy', 'data', 'export', 'delete', 'gdpr', 'retention'],
	},
	{
		category: 'settings',
		title: 'Email Preferences',
		slug: 'email-preferences',
		content: `## Email Preferences

Control which emails you receive from Board of One.

### Email Types

- **Meeting Completed**: Notification when a meeting finishes
- **Action Reminders**: Alerts for upcoming or overdue actions
- **Weekly Digest**: Summary of activity and pending items

### Managing Preferences

1. Go to **Settings** > **Privacy**
2. Toggle each email type on or off
3. Changes save automatically

### Unsubscribe

Every email includes an unsubscribe link. You can also manage preferences from Settings at any time.`,
		keywords: ['email', 'notifications', 'preferences', 'unsubscribe', 'digest'],
	},

	// Troubleshooting
	{
		category: 'troubleshooting',
		title: 'Common Issues',
		slug: 'common-issues',
		content: `## Common Issues

Solutions to frequently encountered problems.

### Meeting Won't Start

- Ensure your question is at least 10 characters
- Check your internet connection
- Try refreshing the page

### Data Upload Fails

- Verify file is CSV format
- Check file size is under 10MB
- Ensure CSV has headers in the first row
- Remove any special characters from headers

### Page Not Loading

- Clear browser cache and cookies
- Try a different browser
- Check if JavaScript is enabled
- Disable browser extensions temporarily

### Actions Not Syncing

- Refresh the page
- Check connection status indicator
- Log out and back in`,
		keywords: ['problem', 'issue', 'error', 'fix', 'help', 'troubleshoot', 'not working'],
	},
	{
		category: 'troubleshooting',
		title: 'Contact Support',
		slug: 'contact-support',
		content: `## Contact Support

Can't find the answer you need? We're here to help.

### Getting Help

1. Check this help center for common solutions
2. Email us at **support@boardofone.com**
3. Include:
   - Description of the issue
   - Steps to reproduce
   - Browser and device info
   - Any error messages

### Response Times

- Most issues addressed within 24 hours
- Critical issues prioritized

### Feature Requests

Have an idea to improve Board of One? We'd love to hear it. Email us with the subject line "Feature Request" and describe your suggestion.`,
		keywords: ['contact', 'support', 'help', 'email', 'feedback', 'report'],
	},
	{
		category: 'actions',
		title: 'Customizing Gantt Chart Colors',
		slug: 'gantt-colors',
		content: `## Customizing Gantt Chart Colors

The Gantt chart offers multiple color coding strategies to help you visualize your action timeline in the way that works best for your team.

### Available Color Strategies

#### By Status (Default)
Color actions based on their current status:
- **Gray**: Not Started - Action hasn't begun yet
- **Blue**: In Progress - Currently being worked on
- **Red**: Blocked - Cannot proceed due to dependencies or obstacles
- **Amber**: On Hold - Temporarily paused
- **Green**: Complete - Finished and closed
- **Gray with strikethrough**: Cancelled - Abandoned or no longer needed

Use this when you want to focus on overall progress and see at a glance which actions are active.

#### By Project
Color actions based on their assigned project:
- Each project gets its own unique color
- Supports up to 20 different projects
- Colors rotate through a vibrant palette to maximize distinction

Use this when you're managing multiple projects simultaneously and want to see which actions belong to which project.

#### By Priority
Color actions based on their priority level:
- **Green**: Low priority - Nice to have, not urgent
- **Amber**: Medium priority - Important but not critical
- **Red**: High priority - Needs immediate attention

Use this when prioritization is critical and you want to focus on high-impact items first.

#### Hybrid Mode
Combines status (primary color) with project information (accent stripe):
- Main bar color represents status
- Accent stripe shows project assignment
- Best of both worlds for complex projects

Use this when you need to see both status AND project information at once.

### How to Change Your Preference

1. Open the Gantt chart in the Actions page
2. Click the color strategy selector at the top of the chart
3. Choose your preferred strategy from the dropdown
4. The chart will immediately update with the new colors
5. Your preference is automatically saved and will persist across sessions

### Tips for Using Color Coding

- **For project-focused teams**: Use "By Project" to quickly identify which actions belong to each project
- **For status tracking**: Use "By Status" (default) to focus on progress and see stalled items
- **For deadline management**: Use "By Priority" to keep high-priority actions front and center
- **For complex projects**: Use "Hybrid" to track both status and project at the same time

### Color Accessibility

All colors are carefully chosen to:
- Provide good contrast on various backgrounds
- Be distinguishable for color-blind viewers
- Maintain readability on different screen sizes

If you find the colors difficult to distinguish, try zooming in your browser or adjusting your screen brightness.`,
		keywords: ['gantt', 'chart', 'color', 'visualization', 'customize', 'strategy', 'project', 'status', 'priority'],
	},
];

/**
 * Search help articles by query
 * Returns articles matching title, content, or keywords
 */
export function searchHelpArticles(query: string): HelpArticle[] {
	if (!query.trim()) return helpArticles;

	const lowerQuery = query.toLowerCase();
	const terms = lowerQuery.split(/\s+/).filter(Boolean);

	return helpArticles.filter((article) => {
		const searchText = [
			article.title,
			article.content,
			...article.keywords,
		]
			.join(' ')
			.toLowerCase();

		return terms.every((term) => searchText.includes(term));
	});
}

/**
 * Get articles for a specific category
 */
export function getArticlesByCategory(categoryId: string): HelpArticle[] {
	return helpArticles.filter((article) => article.category === categoryId);
}

/**
 * Get a single article by slug
 */
export function getArticleBySlug(slug: string): HelpArticle | undefined {
	return helpArticles.find((article) => article.slug === slug);
}
