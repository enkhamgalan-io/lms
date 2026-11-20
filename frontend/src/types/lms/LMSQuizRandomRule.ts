export interface LMSQuizRandomRule {
	creation: string
	name: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Question Bank : Data	*/
	question_bank: string
	/**	Difficulty : Select - Leave empty for any difficulty.	*/
	difficulty?: '' | 'Easy' | 'Medium' | 'Hard'
	/**	Questions : Int	*/
	count: number
}
