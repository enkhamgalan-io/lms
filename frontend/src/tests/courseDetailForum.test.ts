import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const { courseData, shownTabs } = vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		courseData: { value: null as Record<string, unknown> | null },
		shownTabs: { value: [] as string[] },
	}
})

vi.mock('@/stores/settings', () => ({ useSettings: () => ({}) }))
vi.mock('@/stores/user', () => ({ usersStore: () => ({ userResource: {} }) }))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))
vi.mock('frappe-ui', async () => {
	const { reactive } = await import('vue')
	const passthrough = { template: '<div><slot /></div>' }
	return {
		createResource: () =>
			reactive({ data: courseData.value, loading: false, reload: vi.fn() }),
		usePageMeta: vi.fn(),
		toast: { success: vi.fn(), error: vi.fn() },
		Badge: passthrough,
		Button: passthrough,
		Dropdown: passthrough,
		Tooltip: passthrough,
	}
})
vi.mock('@framework/ui/telemetry/index', () => ({
	useTelemetry: () => ({ capture: vi.fn() }),
}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({
	useOnboarding: () => ({ updateOnboardingStep: vi.fn() }),
}))

const { stub } = vi.hoisted(() => ({
	stub: () => ({ default: { render: () => null } }),
}))
// The page decides which tabs exist; the layout shows the ones whose `when` holds.
vi.mock('@/components/Layouts/pages/TabbedDetailPage.vue', () => ({
	default: {
		props: ['tabs'],
		setup(props: { tabs: { key: string; when?: boolean }[] }) {
			return () => {
				shownTabs.value = props.tabs
					.filter((tab) => tab.when !== false)
					.map((tab) => tab.key)
				return null
			}
		},
	},
}))
vi.mock('@/pages/Courses/CourseEditor.vue', stub)
vi.mock('@/pages/Courses/CourseOverview.vue', stub)
vi.mock('@/pages/Courses/CourseDashboard.vue', stub)
vi.mock('@/pages/Courses/CourseForm.vue', stub)
vi.mock('@/components/Discussions.vue', stub)
vi.mock('@/components/SkeletonLoader.vue', stub)
vi.mock('@/components/LessonHelp.vue', stub)
vi.mock('@/components/ShortcutTooltip.vue', stub)
vi.mock('@/components/HeaderButton.vue', stub)

import CourseDetail from '@/pages/Courses/CourseDetail.vue'

const discussions = {
	'Discussion Topic': { read: true },
	'Discussion Reply': { read: true },
}

const tabsFor = async (
	membership: unknown,
	permissions: Record<string, unknown> = discussions
) => {
	courseData.value = {
		name: 'COURSE-1',
		title: 'Law',
		membership,
		instructors: [],
	}
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{
				path: '/courses/:courseName',
				name: 'CourseDetail',
				component: { render: () => null },
			},
		],
	})
	await router.push('/courses/COURSE-1')
	mount(CourseDetail, {
		props: { courseName: 'COURSE-1' },
		global: {
			plugins: [router],
			provide: {
				$user: {
					data: { name: 'lee@example.com', username: 'lee', permissions },
				},
			},
			mocks: { __: (globalThis as any).__ },
		},
	})
	await flushPromises()
	return shownTabs.value
}

describe("the course's forum tab", () => {
	it('opens for an enrolled learner, beside the overview', async () => {
		expect(await tabsFor({ name: 'ENR-1' })).toEqual([
			'overview',
			'discussions',
		])
	})

	it('stays away from a learner who is not enrolled', async () => {
		expect(await tabsFor(null)).toEqual([])
	})

	it('stays away from someone who cannot read discussions', async () => {
		expect(await tabsFor({ name: 'ENR-1' }, {})).toEqual([])
	})
})
